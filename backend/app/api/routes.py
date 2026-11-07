import difflib, io, json, zipfile
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db import get_db
from app.config import settings
from app.models import (
    User,
    Project,
    Requirement,
    Run,
    AgentTask,
    AgentExecution,
    GeneratedFile,
    CodeReview,
    TestResult,
    Document,
    ProjectVersion,
    Approval,
    AuditEvent,
    now,
)
from app.schemas import (
    Register,
    Login,
    ProjectInput,
    ProjectUpdate,
    Execute,
    Decision,
    FileChange,
    ImportFiles,
    RequirementInput,
    TestRequest,
    ProposalEdit,
)
from app.security import (
    current_user,
    check_origin,
    rate_limit,
    hasher,
    password_ok,
    make_token,
)
from app.services.artifacts import (
    owned,
    latest_files,
    latest_docs,
    file_payload,
    source_hash,
    save_doc,
    apply_files,
    bump_version,
    propose,
    event,
    digest,
    validate_files,
    invalidate,
)
from app.services.orchestration import ROUTES

from app import contracts as out

router = APIRouter(prefix="/api")


def row(obj, exclude=()):
    return {
        c.name: getattr(obj, c.name)
        for c in obj.__table__.columns
        if c.name not in exclude
    }


def ensure_idle(db, pid):
    if db.scalar(
        select(Run.id).where(
            Run.project_id == pid,
            Run.status.in_(["queued", "running", "awaiting_approval", "testing"]),
        )
    ):
        raise HTTPException(409, "Finish or cancel the active workflow first")
    if db.scalar(
        select(Approval.id).where(
            Approval.project_id == pid, Approval.status == "pending"
        )
    ):
        raise HTTPException(409, "Resolve the pending proposal first")


def expected(project, revision):
    if project.revision != revision:
        raise HTTPException(
            409, "Project changed. Refresh before applying this action."
        )


def login_response(user, response):
    token, csrf = make_token(user)
    response.set_cookie(
        "devsphere_session",
        token,
        httponly=True,
        secure=settings().secure_cookie,
        samesite="strict",
        max_age=8 * 3600,
        path="/",
    )
    return {
        "user": row(user, ("password_hash",)),
        "csrf_token": csrf,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post(
    "/auth/register",
    status_code=201,
    tags=["Authentication"],
    response_model=out.AuthResponse,
)
def register(
    data: Register, request: Request, response: Response, db: Session = Depends(get_db)
):
    check_origin(request)
    rate_limit("register:" + request.client.host, 5, 3600)
    if not settings().registration_enabled:
        raise HTTPException(403, "Registration is disabled for this demonstration")
    user = User(
        name=data.name.strip(),
        email=str(data.email).lower(),
        password_hash=hasher.hash(data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")
    return login_response(user, response)


@router.post("/auth/login", tags=["Authentication"], response_model=out.AuthResponse)
def login(
    data: Login, request: Request, response: Response, db: Session = Depends(get_db)
):
    check_origin(request)
    rate_limit("login:" + request.client.host, 10, 60)
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if not user or not password_ok(data.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return login_response(user, response)


@router.get("/auth/me", tags=["Authentication"], response_model=out.MeResponse)
def me(request: Request, user=Depends(current_user)):
    return {"user": row(user, ("password_hash",)), "csrf_token": request.state.csrf}


@router.post("/auth/logout", status_code=204, tags=["Authentication"])
def logout(response: Response, user=Depends(current_user)):
    response.delete_cookie("devsphere_session", path="/")


@router.get("/settings", tags=["System"], response_model=out.SettingsResponse)
def capabilities(db: Session = Depends(get_db), user=Depends(current_user)):
    beat = db.scalar(
        select(AuditEvent)
        .where(AuditEvent.event_type == "runner_heartbeat")
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    online = bool(beat and beat.created_at > now() - timedelta(seconds=30))
    cfg = settings()
    return {
        "provider": cfg.provider,
        "model": cfg.ollama_model if cfg.provider == "ollama" else cfg.openai_model,
        "models": [cfg.ollama_model]
        if cfg.provider == "ollama"
        else [cfg.openai_model],
        "runner_online": online,
        "sandbox_enabled": cfg.sandbox_enabled,
        "runner_capabilities": beat.event_data if online else {},
        "registration_enabled": cfg.registration_enabled,
        "max_files": cfg.max_files,
        "max_project_bytes": cfg.max_project_bytes,
        "version": "1.0.0",
    }


@router.post(
    "/projects", status_code=201, tags=["Projects"], response_model=out.ProjectResponse
)
def create_project(
    data: ProjectInput, db: Session = Depends(get_db), user=Depends(current_user)
):
    rate_limit("projects:" + user.id, 15, 3600)
    valid = {
        "Python": {"FastAPI", "React + FastAPI"},
        "JavaScript": {"Node.js", "React + Node.js"},
        "Java": {"Java standard library"},
    }
    if data.framework not in valid[data.programming_language]:
        raise HTTPException(422, "Language and framework do not match")
    p = Project(user_id=user.id, **data.model_dump())
    db.add(p)
    db.flush()
    db.add(
        ProjectVersion(
            project_id=p.id,
            version_number=1,
            change_summary="Created project",
            manifest={},
        )
    )
    event(db, p.id, "project_created", {}, user.id)
    db.commit()
    return row(p)


@router.get("/projects", tags=["Projects"], response_model=list[out.ProjectResponse])
def projects(
    db: Session = Depends(get_db),
    user=Depends(current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return [
        row(p)
        for p in db.scalars(
            select(Project)
            .where(Project.user_id == user.id, Project.deleted.is_(False))
            .order_by(Project.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ]


@router.get(
    "/projects/{project_id}", tags=["Projects"], response_model=out.ProjectResponse
)
def project(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    return row(owned(db, project_id, user))


@router.put(
    "/projects/{project_id}", tags=["Projects"], response_model=out.ProjectResponse
)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = owned(db, project_id, user, True)
    ensure_idle(db, p.id)
    expected(p, data.expected_revision)
    p.project_name = data.project_name
    p.description = data.description
    invalidate(db, p, "brief")
    bump_version(db, p, "Updated project requirement")
    event(db, p.id, "project_updated", {}, user.id)
    db.commit()
    return row(p)


@router.delete("/projects/{project_id}", status_code=204, tags=["Projects"])
def delete_project(
    project_id: str,
    confirm_name: str,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = owned(db, project_id, user, True)
    ensure_idle(db, p.id)
    if confirm_name != p.project_name:
        raise HTTPException(409, "Type the exact project name to confirm deletion")
    p.deleted = True
    event(db, p.id, "project_deleted", {}, user.id)
    db.commit()


def start(db, p, user, workflow, instructions=""):
    rate_limit("workflow:" + user.id, 12, 3600)
    ensure_idle(db, p.id)
    docs = latest_docs(db, p.id)
    files = latest_files(db, p.id)
    prerequisite = {
        "architecture": ["requirements"],
        "database": ["requirements", "architecture"],
        "code": ["requirements", "architecture", "database"],
    }
    missing = [name for name in prerequisite.get(workflow, []) if name not in docs]
    if missing:
        raise HTTPException(
            409, "Approve required artifacts first: " + ", ".join(missing)
        )
    if workflow in {"review", "quick_review", "security", "tests", "repair"} and not files:
        raise HTTPException(409, "Import or generate and approve source files first")
    r = Run(
        project_id=p.id,
        workflow_type=workflow,
        request={"instructions": instructions},
        source_hash=source_hash(db, p.id),
    )
    db.add(r)
    p.project_status = "working"
    db.flush()
    event(db, p.id, "workflow_queued", {"run_id": r.id, "type": workflow}, user.id)
    db.commit()
    return {
        "run_id": r.id,
        "status": r.status,
        "status_url": f"/api/projects/{p.id}/workflow",
    }


@router.post(
    "/projects/{project_id}/execute",
    status_code=202,
    tags=["Workflows"],
    response_model=out.StartResponse,
)
def execute(
    project_id: str,
    data: Execute,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return start(
        db,
        owned(db, project_id, user, True),
        user,
        data.workflow_type,
        data.instructions,
    )


@router.get(
    "/projects/{project_id}/workflow",
    tags=["Workflows"],
    response_model=out.WorkflowResponse,
)
def workflow(
    project_id: str, db: Session = Depends(get_db), user=Depends(current_user)
):
    owned(db, project_id, user)
    r = db.scalar(
        select(Run)
        .where(Run.project_id == project_id)
        .order_by(Run.created_at.desc())
        .limit(1)
    )
    if not r:
        return {"run": None, "tasks": [], "approvals": []}
    tasks = db.scalars(
        select(AgentTask).where(AgentTask.run_id == r.id).order_by(AgentTask.created_at)
    ).all()
    approvals = db.scalars(
        select(Approval)
        .where(Approval.project_id == project_id, Approval.status == "pending")
        .order_by(Approval.created_at)
    ).all()
    return {
        "run": {**row(r), "stages": ROUTES[r.workflow_type]},
        "tasks": [row(t, ("input_data",)) for t in tasks],
        "approvals": [row(a) for a in approvals],
    }


@router.get(
    "/projects/{project_id}/status",
    tags=["Workflows"],
    response_model=out.StatusResponse,
)
def status(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    p = owned(db, project_id, user)
    return {"status": p.project_status, "revision": p.revision}


@router.post(
    "/projects/{project_id}/cancel",
    status_code=200,
    tags=["Workflows"],
    response_model=out.StatusResponse,
)
def cancel(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    p = owned(db, project_id, user, True)
    for r in db.scalars(
        select(Run).where(
            Run.project_id == p.id,
            Run.status.in_(["running", "queued", "awaiting_approval", "testing"]),
        )
    ):
        r.status = "cancelled"
    for a in db.scalars(
        select(Approval).where(
            Approval.project_id == p.id, Approval.status == "pending"
        )
    ):
        a.status = "cancelled"
    for t in db.scalars(
        select(TestResult).where(
            TestResult.project_id == p.id,
            TestResult.test_status.in_(["queued", "running"]),
        )
    ):
        t.test_status = "cancelled"
    p.project_status = "draft"
    event(db, p.id, "workflow_cancelled", {}, user.id)
    db.commit()
    return {"status": "cancelled"}


@router.post(
    "/projects/{project_id}/retry",
    status_code=202,
    tags=["Workflows"],
    response_model=out.StartResponse,
)
def retry(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    p = owned(db, project_id, user, True)
    ensure_idle(db, p.id)
    r = db.scalar(
        select(Run)
        .where(Run.project_id == p.id, Run.status == "failed")
        .order_by(Run.created_at.desc())
        .limit(1)
    )
    if not r:
        raise HTTPException(409, "No failed workflow to retry")
    r.status = "queued"
    r.error = None
    p.project_status = "working"
    event(db, p.id, "workflow_retry", {"run_id": r.id}, user.id)
    db.commit()
    return {"run_id": r.id, "status": "queued"}


@router.get(
    "/projects/{project_id}/agent-tasks",
    tags=["Workflows"],
    response_model=list[out.DetailedTaskResponse],
)
@router.get(
    "/projects/{project_id}/agents",
    tags=["Workflows"],
    response_model=list[out.DetailedTaskResponse],
)
def tasks(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    owned(db, project_id, user)
    return [
        {
            **row(t),
            "executions": [
                row(e)
                for e in db.scalars(
                    select(AgentExecution).where(AgentExecution.agent_task_id == t.id)
                )
            ],
        }
        for t in db.scalars(
            select(AgentTask)
            .where(AgentTask.project_id == project_id)
            .order_by(AgentTask.created_at.desc())
            .limit(100)
        )
    ]


def workflow_endpoint(kind):
    def endpoint(
        project_id: str,
        data: Execute | None = None,
        db: Session = Depends(get_db),
        user=Depends(current_user),
    ):
        return start(
            db,
            owned(db, project_id, user, True),
            user,
            kind,
            data.instructions if data else "",
        )

    endpoint.__name__ = "start_" + kind
    return endpoint


for path, kind in [
    ("design", "architecture"),
    ("database-design", "database"),
    ("generate-code", "code"),
    ("review", "review"),
    ("security-analysis", "security"),
    ("generate-tests", "tests"),
    ("documentation", "documentation"),
]:
    router.add_api_route(
        "/projects/{project_id}/" + path,
        workflow_endpoint(kind),
        methods=["POST"],
        status_code=202,
        tags=["Engineering"],
        response_model=out.StartResponse,
    )


@router.get(
    "/projects/{project_id}/requirements",
    tags=["Artifacts"],
    response_model=list[out.RequirementResponse],
)
def requirements(
    project_id: str, db: Session = Depends(get_db), user=Depends(current_user)
):
    owned(db, project_id, user)
    return [
        row(r)
        for r in db.scalars(
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .order_by(Requirement.version.desc())
        )
    ]


@router.post(
    "/projects/{project_id}/requirements",
    status_code=202,
    tags=["Artifacts"],
    response_model=out.ApprovalResponse,
)
def edit_requirement(
    project_id: str,
    data: RequirementInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = owned(db, project_id, user, True)
    ensure_idle(db, p.id)
    expected(p, data.expected_revision)
    a = propose(
        db, p, "requirements", {"summary": data.content, "source": "human_edit"}
    )
    db.commit()
    return row(a)


@router.get(
    "/projects/{project_id}/files",
    tags=["Files"],
    response_model=list[out.FileResponse],
)
def files(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    owned(db, project_id, user)
    return [row(f) for f in latest_files(db, project_id)]


@router.get(
    "/projects/{project_id}/files/{file_id}",
    tags=["Files"],
    response_model=out.FileResponse,
)
def file(
    project_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    owned(db, project_id, user)
    f = db.get(GeneratedFile, file_id)
    if not f or f.project_id != project_id:
        raise HTTPException(404, "File not found")
    return row(f)


@router.put(
    "/projects/{project_id}/files/{file_id}",
    status_code=202,
    tags=["Files"],
    response_model=out.ApprovalResponse,
)
def change_file(
    project_id: str,
    file_id: str,
    data: FileChange,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = owned(db, project_id, user, True)
    ensure_idle(db, p.id)
    expected(p, data.expected_revision)
    f = db.get(GeneratedFile, file_id)
    if not f or f.project_id != p.id:
        raise HTTPException(404, "File not found")
    current = {x.file_path: x for x in latest_files(db, p.id)}
    if current[f.file_path].id != f.id:
        raise HTTPException(409, "This is an old file version")
    payload = {
        "files": [{"path": f.file_path, "content": data.content}],
        "summary": "Manual file edit",
    }
    validate_files(payload["files"])
    a = propose(db, p, "code", payload)
    db.commit()
    return row(a)


@router.post(
    "/projects/{project_id}/files/import",
    status_code=202,
    tags=["Files"],
    response_model=out.ApprovalResponse,
)
def import_files(
    project_id: str,
    data: ImportFiles,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = owned(db, project_id, user, True)
    ensure_idle(db, p.id)
    expected(p, data.expected_revision)
    payload = {
        "files": [f.model_dump() for f in data.files],
        "summary": "Import source files",
    }
    validate_files(payload["files"])
    a = propose(db, p, "code", payload)
    db.commit()
    return row(a)


@router.get(
    "/projects/{project_id}/files/{file_id}/diff",
    tags=["Files"],
    response_model=out.DiffResponse,
)
def diff(
    project_id: str,
    file_id: str,
    against: int = Query(ge=1),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    f = file(project_id, file_id, db, user)
    other = db.scalar(
        select(GeneratedFile).where(
            GeneratedFile.project_id == project_id,
            GeneratedFile.file_path == f["file_path"],
            GeneratedFile.version == against,
        )
    )
    if not other:
        raise HTTPException(404, "Version not found")
    return {
        "before": other.file_content,
        "after": f["file_content"],
        "diff": "\n".join(
            difflib.unified_diff(
                other.file_content.splitlines(),
                f["file_content"].splitlines(),
                fromfile=f"v{against}",
                tofile=f"v{f['version']}",
            )
        ),
    }


@router.get(
    "/projects/{project_id}/reviews",
    tags=["Quality"],
    response_model=list[out.ReviewResponse],
)
def reviews(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    owned(db, project_id, user)
    current_ids = {f.id for f in latest_files(db, project_id)}
    return [
        {
            **row(r),
            "source_current": bool(r.file_id and r.file_id in current_ids),
        }
        for r in db.scalars(
            select(CodeReview)
            .where(CodeReview.project_id == project_id)
            .order_by(CodeReview.created_at.desc())
            .limit(200)
        )
    ]


@router.get(
    "/projects/{project_id}/tests",
    tags=["Quality"],
    response_model=list[out.TestResponse],
)
def tests(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    owned(db, project_id, user)
    current_hash = source_hash(db, project_id)
    return [
        {**row(t), "source_current": t.source_hash == current_hash}
        for t in db.scalars(
            select(TestResult)
            .where(TestResult.project_id == project_id)
            .order_by(TestResult.created_at.desc())
            .limit(50)
        )
    ]


@router.post(
    "/projects/{project_id}/run-tests",
    status_code=202,
    tags=["Quality"],
    response_model=out.ApprovalResponse,
)
def request_tests(
    project_id: str,
    data: TestRequest,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = owned(db, project_id, user, True)
    ensure_idle(db, p.id)
    if not latest_files(db, p.id):
        raise HTTPException(409, "No source files")
    if not settings().sandbox_enabled:
        raise HTTPException(503, "Sandbox runner disabled")
    a = propose(
        db,
        p,
        "test_execution",
        {"recipe": data.recipe, "source_hash": source_hash(db, p.id)},
    )
    db.commit()
    return row(a)


@router.get(
    "/projects/{project_id}/documents",
    tags=["Documentation"],
    response_model=list[out.DocumentResponse],
)
def documents(
    project_id: str,
    db: Session = Depends(get_db),
    user=Depends(current_user),
    history: bool = False,
):
    owned(db, project_id, user)
    items = (
        db.scalars(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
        ).all()
        if history
        else latest_docs(db, project_id).values()
    )
    return [row(d) for d in items]


@router.get(
    "/projects/{project_id}/documents/{document_id}/download", tags=["Documentation"]
)
def download_document(
    project_id: str,
    document_id: str,
    format: str = Query("md", pattern="^(md|pdf)$"),
    section: str = Query(
        "final_report",
        pattern="^(final_report|readme|architecture|testing|deployment)$",
    ),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    owned(db, project_id, user)
    d = db.get(Document, document_id)
    if not d or d.project_id != project_id:
        raise HTTPException(404, "Document not found")
    from app.services.exports import markdown_document, pdf_document

    md = markdown_document(d.document_type, d.document_content, section)
    filename = section if d.document_type == "documentation" else d.document_type
    if format == "md":
        return Response(
            md,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}-v{d.version}.md"'
            },
        )
    return Response(
        pdf_document(md),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}-v{d.version}.pdf"'
        },
    )


@router.get(
    "/projects/{project_id}/versions",
    tags=["History"],
    response_model=list[out.VersionResponse],
)
def versions(
    project_id: str, db: Session = Depends(get_db), user=Depends(current_user)
):
    owned(db, project_id, user)
    return [
        row(v)
        for v in db.scalars(
            select(ProjectVersion)
            .where(ProjectVersion.project_id == project_id)
            .order_by(ProjectVersion.version_number.desc())
        )
    ]


@router.get(
    "/projects/{project_id}/events",
    tags=["History"],
    response_model=list[out.EventResponse],
)
def events(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    owned(db, project_id, user)
    return [
        row(e)
        for e in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.project_id == project_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(100)
        )
    ]


@router.get(
    "/projects/{project_id}/approvals",
    tags=["Approvals"],
    response_model=list[out.ApprovalResponse],
)
def approvals(
    project_id: str, db: Session = Depends(get_db), user=Depends(current_user)
):
    owned(db, project_id, user)
    return [
        row(a)
        for a in db.scalars(
            select(Approval)
            .where(Approval.project_id == project_id)
            .order_by(Approval.created_at.desc())
            .limit(100)
        )
    ]


@router.put(
    "/projects/{project_id}/approvals/{approval_id}",
    tags=["Approvals"],
    response_model=out.ApprovalResponse,
)
def edit_proposal(
    project_id: str,
    approval_id: str,
    data: ProposalEdit,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    from app.schemas import Plan, SRS, Architecture, DatabaseDesign, CodeBundle
    from openapi_spec_validator import validate

    p = owned(db, project_id, user, True)
    a = db.scalar(
        select(Approval)
        .where(Approval.id == approval_id, Approval.project_id == p.id)
        .with_for_update()
    )
    if not a:
        raise HTTPException(404, "Proposal not found")
    expected(p, data.expected_revision)
    if (
        a.status != "pending"
        or a.base_revision != p.revision
        or a.artifact_hash != data.artifact_hash
    ):
        raise HTTPException(409, "Proposal changed; refresh first")
    schemas = {
        "plan": Plan,
        "requirements": SRS,
        "architecture": Architecture,
        "database": DatabaseDesign,
        "code": CodeBundle,
        "tests": CodeBundle,
    }
    if a.checkpoint not in schemas:
        raise HTTPException(422, "This checkpoint cannot be edited")
    payload = schemas[a.checkpoint].model_validate(data.payload).model_dump()
    if a.checkpoint in {"code", "tests"}:
        validate_files(payload["files"])
    if a.checkpoint == "database":
        validate(json.loads(payload["openapi_json"]))
    previous_hash = a.artifact_hash
    # Original model output remains immutable in AgentTask.output_data; every human edit is auditable.
    event(
        db,
        p.id,
        "proposal_edited",
        {
            "approval_id": a.id,
            "previous_hash": previous_hash,
            "previous_payload": a.payload,
            "new_hash": digest(payload),
        },
        user.id,
    )
    a.payload = payload
    a.artifact_hash = digest(payload)
    db.commit()
    return row(a)


@router.post(
    "/projects/{project_id}/approvals/{approval_id}/decision",
    tags=["Approvals"],
    response_model=out.StatusResponse,
)
def decide(
    project_id: str,
    approval_id: str,
    data: Decision,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = owned(db, project_id, user, True)
    a = db.scalar(
        select(Approval)
        .where(Approval.id == approval_id, Approval.project_id == p.id)
        .with_for_update()
    )
    if not a:
        raise HTTPException(404, "Approval not found")
    expected(p, data.expected_revision)
    if (
        a.status != "pending"
        or a.base_revision != p.revision
        or a.artifact_hash != data.artifact_hash
    ):
        raise HTTPException(409, "Proposal changed or is no longer pending")
    run = db.get(Run, a.run_id) if a.run_id else None
    a.status = {
        "approve": "approved",
        "reject": "rejected",
        "regenerate": "regeneration_requested",
    }[data.decision]
    a.comment = data.comment
    a.decided_by = user.id
    a.decided_at = now()
    if data.decision == "approve":
        invalidate(db, p, a.checkpoint)
        if a.checkpoint in {"code", "tests"}:
            apply_files(db, p, a.payload["files"])
            bump_version(db, p, "Approved " + a.checkpoint + " proposal")
        elif a.checkpoint in {"plan", "requirements", "architecture", "database"}:
            save_doc(db, p, a.checkpoint, a.payload)
            bump_version(db, p, "Approved " + a.checkpoint)
        elif a.checkpoint == "test_execution":
            if not settings().sandbox_enabled:
                raise HTTPException(503, "Sandbox runner disabled")
            if a.payload["source_hash"] != source_hash(db, p.id):
                raise HTTPException(409, "Source changed since the test proposal")
            t = TestResult(
                project_id=p.id,
                run_id=a.run_id,
                source_hash=a.payload["source_hash"],
                recipe=a.payload["recipe"],
                details={
                    "files": file_payload(db, p.id),
                    "approval_id": a.id,
                    "approved_by": user.id,
                },
            )
            db.add(t)
        if run:
            if a.checkpoint == "test_execution":
                run.status = "testing"
                p.project_status = "testing"
            else:
                run.stage += 1
                run.status = "queued"
                p.project_status = "working"
                if run.stage >= len(ROUTES[run.workflow_type]):
                    run.status = "completed"
                    p.project_status = (
                        "completed" if a.checkpoint == "delivery" else "ready"
                    )
        else:
            p.project_status = "ready"
    elif data.decision == "regenerate" and run:
        if not data.comment.strip():
            raise HTTPException(422, "Explain the requested change")
        if a.checkpoint == "test_failure":
            run.status = "cancelled"
            db.flush()
            new = Run(
                project_id=p.id,
                workflow_type="repair",
                request={"instructions": data.comment},
                source_hash=source_hash(db, p.id),
            )
            db.add(new)
        else:
            target_stage = {"delivery": "documentation", "test_execution": "tests"}.get(
                a.checkpoint, a.checkpoint
            )
            if target_stage != a.checkpoint:
                run.stage = ROUTES[run.workflow_type].index(target_stage)
            tasknames = {
                "documentation": ["documentation"],
                "plan": ["plan"],
                "code": ["code"],
                "tests": ["tests"],
                "requirements": ["requirements"],
                "architecture": ["architecture"],
                "database": ["database"],
            }.get(target_stage, [])
            for t in db.scalars(
                select(AgentTask).where(
                    AgentTask.run_id == run.id, AgentTask.task_name.in_(tasknames)
                )
            ):
                t.task_status = "superseded"
            run.request = {
                **run.request,
                "stage_instructions": {
                    **run.request.get("stage_instructions", {}),
                    target_stage: data.comment,
                },
            }
            run.status = "queued"
        p.project_status = "working"
    else:
        if run:
            run.status = "cancelled"
        p.project_status = "draft"
    event(
        db,
        p.id,
        "approval_decided",
        {
            "approval_id": a.id,
            "checkpoint": a.checkpoint,
            "decision": data.decision,
            "hash": a.artifact_hash,
        },
        user.id,
    )
    db.commit()
    return {"status": a.status, "revision": p.revision}


@router.get("/projects/{project_id}/export", tags=["Files"])
def export(project_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    p = owned(db, project_id, user)
    buf = io.BytesIO()
    from app.services.exports import markdown_document

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in latest_files(db, p.id):
            z.writestr(f.file_path, f.file_content)
        for kind, d in latest_docs(db, p.id).items():
            if kind == "documentation":
                for section in [
                    "readme",
                    "architecture",
                    "testing",
                    "deployment",
                    "final_report",
                ]:
                    z.writestr(
                        "devsphere-reports/delivery/" + section + ".md",
                        markdown_document(kind, d.document_content, section),
                    )
            else:
                z.writestr(
                    "devsphere-reports/" + kind + ".md",
                    markdown_document(kind, d.document_content),
                )
        z.writestr(
            "devsphere-reports/manifest.json",
            json.dumps(
                {
                    "project": p.project_name,
                    "revision": p.revision,
                    "source_hash": source_hash(db, p.id),
                    "files": {
                        f.file_path: f.content_hash for f in latest_files(db, p.id)
                    },
                },
                indent=2,
            ),
        )
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="devsphere-project.zip"'},
    )
