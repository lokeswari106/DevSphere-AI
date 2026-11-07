import asyncio, importlib, logging, time
from datetime import timedelta
from sqlalchemy import select
from app.db import Session
from app.models import (
    Project,
    Run,
    AgentTask,
    AgentExecution,
    CodeReview,
    TestResult,
    Approval,
    now,
)
from app.services.artifacts import (
    latest_docs,
    file_payload,
    source_hash,
    save_doc,
    propose,
    event,
)
from app.config import settings

log = logging.getLogger("devsphere.workflow")
ROUTES = {
    "quick_review": ["quality"],
    "full": [
        "plan",
        "requirements",
        "architecture",
        "database",
        "code",
        "quality",
        "tests",
        "execute_tests",
        "documentation",
        "delivery",
    ],
    "review": ["plan", "quality", "documentation", "delivery"],
    "security": ["plan", "security", "documentation", "delivery"],
    "requirements": ["plan", "requirements"],
    "architecture": ["plan", "architecture"],
    "database": ["plan", "database"],
    "code": ["plan", "code", "quality", "documentation", "delivery"],
    "tests": ["plan", "tests", "execute_tests", "documentation", "delivery"],
    "documentation": ["plan", "documentation", "delivery"],
    "repair": [
        "plan",
        "code",
        "quality",
        "tests",
        "execute_tests",
        "documentation",
        "delivery",
    ],
}
MODULES = {
    "plan": "orchestrator",
    "requirements": "requirements",
    "architecture": "architecture",
    "database": "database",
    "code": "code",
    "review": "review",
    "security": "security",
    "tests": "testing_documentation",
    "documentation": "testing_documentation",
}
GATED = {"plan", "requirements", "architecture", "database", "code", "tests"}


def build_context(db, project, run, stage):
    docs = latest_docs(db, project.id)
    outputs = {
        k: v.document_content
        for k, v in docs.items()
        if k in {"plan", "requirements", "architecture", "database"}
    }
    tests = db.scalars(
        select(TestResult)
        .where(TestResult.project_id == project.id)
        .order_by(TestResult.created_at.desc())
        .limit(3)
    ).all()
    reviews = db.scalars(
        select(CodeReview)
        .where(CodeReview.project_id == project.id)
        .order_by(CodeReview.created_at.desc())
        .limit(25)
    ).all()
    context = {
        "project_id": project.id,
        "run_id": run.id,
        "original_requirement": project.description,
        "assignment": stage,
        "workflow": run.workflow_type,
        "instructions": run.request.get("instructions", "")
        + "\nStage feedback: "
        + run.request.get("stage_instructions", {}).get(stage, ""),
        "language": project.programming_language,
        "framework": project.framework,
        "approved_outputs": outputs,
        "source_hash": source_hash(db, project.id),
        "constraints": {
            "max_files": settings().max_files,
            "human_approval_required": True,
            "execution": "sandbox only",
            "network_in_tests": False,
            "python_test_packages": ["pytest", "fastapi", "httpx", "sqlalchemy", "pydantic", "python-multipart", "bcrypt", "python-jose"],
            "python_test_style": "Synchronous pytest functions with TestClient; no pytest-asyncio plugin. sqlite3 is part of the standard library.",
        },
    }
    if stage in {"code", "review", "security", "tests", "documentation"}:
        context["files"] = file_payload(db, project.id)
        context["recent_tests"] = [
            {
                "status": t.test_status,
                "source_hash": t.source_hash,
                "total": t.total_tests,
                "passed": t.passed_tests,
                "failed": t.failed_tests,
                "log": t.execution_output[-10000:],
            }
            for t in tests
        ]
        context["reviews"] = [
            {
                "file": r.file_path,
                "severity": r.severity,
                "issue": r.issue_description,
                "fix": r.suggested_fix,
                "evidence": r.evidence_status,
            }
            for r in reviews
        ]
    decisions = db.scalars(
        select(Approval)
        .where(Approval.project_id == project.id, Approval.status == "approved")
        .order_by(Approval.created_at.desc())
        .limit(20)
    ).all()
    context["user_decisions"] = [
        {
            "checkpoint": a.checkpoint,
            "comment": a.comment,
            "artifact_hash": a.artifact_hash,
        }
        for a in decisions
        if a.comment
    ]
    # Never silently truncate a source file; stop clearly when context exceeds the budget.
    import json

    if len(json.dumps(context)) > 110000:
        raise ValueError(
            "Project context exceeds the current model budget. Select a smaller source set."
        )
    return context


async def perform(run_id, stage):
    with Session() as db:
        run = db.get(Run, run_id)
        project = db.get(Project, run.project_id)
        if run.status != "running":
            return None
        existing = db.scalar(
            select(AgentTask)
            .where(
                AgentTask.run_id == run_id,
                AgentTask.task_name == stage,
                AgentTask.task_status == "completed",
            )
            .order_by(AgentTask.completed_at.desc())
        )
        if existing:
            return existing.output_data
        context = build_context(db, project, run, stage)
        task = AgentTask(
            project_id=project.id,
            run_id=run.id,
            agent_name=MODULES[stage],
            task_name=stage,
            task_status="running",
            input_data=context,
            started_at=now(),
        )
        db.add(task)
        db.flush()
        context = {**context, "task_id": task.id}
        task_id = task.id
        pid = project.id
        event(
            db,
            pid,
            "agent_started",
            {"task_id": task.id, "agent": MODULES[stage], "assignment": stage},
        )
        db.commit()
    for attempt in range(3):
        started = time.monotonic()
        with Session() as db:
            execution = AgentExecution(
                project_id=pid,
                agent_task_id=task_id,
                execution_status="running",
                retry_count=attempt,
                execution_logs={"event": "model_request_started"},
            )
            db.add(execution)
            db.commit()
            exid = execution.id
        try:
            module = importlib.import_module("app.agents." + MODULES[stage])
            output, usage = await module.execute(context)
            with Session() as db:
                run = db.get(Run, run_id)
                if run.status != "running":
                    ex = db.get(AgentExecution, exid)
                    ex.execution_status = "cancelled"
                    db.commit()
                    return None
                task = db.get(AgentTask, task_id)
                task.task_status = "completed"
                task.error_message = None
                task.completed_at = now()
                task.output_data = {
                    "agent_id": MODULES[stage],
                    "task_id": task_id,
                    "status": "completed",
                    "artifact": output,
                    "usage": usage,
                    "warnings": output.get("limitations", []),
                }
                ex = db.get(AgentExecution, exid)
                ex.execution_status = "completed"
                ex.execution_time = time.monotonic() - started
                ex.execution_logs = {"usage": usage, "schema_validated": True}
                event(
                    db,
                    pid,
                    "agent_completed",
                    {
                        "task_id": task_id,
                        "agent": MODULES[stage],
                        "duration_seconds": ex.execution_time,
                    },
                )
                db.commit()
                return task.output_data
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Never persist provider request headers, tokens or full transport exceptions.
            message = f"{type(exc).__name__}: {str(exc)[:600]}"
            if "api.openai.com" in message:
                message = "Provider request failed; check credentials, quota and model configuration."
            with Session() as db:
                ex = db.get(AgentExecution, exid)
                ex.execution_status = "failed"
                ex.execution_time = time.monotonic() - started
                ex.execution_logs = {"error": message}
                task = db.get(AgentTask, task_id)
                task.error_message = message
                if attempt == 2:
                    task.task_status = "failed"
                    task.completed_at = now()
                event(
                    db,
                    pid,
                    "agent_retry" if attempt < 2 else "agent_failed",
                    {"task_id": task_id, "attempt": attempt + 1, "error": message},
                )
                db.commit()
            context = {**context, "validation_feedback": message}
            if hasattr(exc, "failed_artifact"):
                context["previous_invalid_artifact"] = exc.failed_artifact
            if attempt < 2:
                await asyncio.sleep(2**attempt)
            else:
                raise ValueError(message) from exc


def persist_findings(db, project, run, kind, result):
    from app.services.artifacts import latest_files

    files = {f.file_path: f for f in latest_files(db, project.id)}
    for f in result["artifact"]["findings"]:
        file = files.get(f["file_path"])
        if not file:
            continue
        line = f.get("line_number")
        if line is not None and not 1 <= line <= len(file.file_content.splitlines()):
            line = None
        db.add(
            CodeReview(
                project_id=project.id,
                run_id=run.id,
                file_id=file.id,
                file_path=file.file_path,
                line_number=line,
                severity=f["severity"],
                issue_type=kind + ":" + f["issue_type"],
                issue_description=f["description"],
                suggested_fix=f["suggested_fix"],
                improved_code=f["improved_code"],
                evidence_status="static_observation"
                if f["issue_type"] == "static_pattern"
                else "ai_hypothesis",
            )
        )


async def advance(run_id):
    try:
        with Session() as db:
            run = db.get(Run, run_id)
            stage = ROUTES[run.workflow_type][run.stage]
            pid = run.project_id
        if stage == "quality":
            # Independent agents read the same approved snapshot; provider concurrency may serialize local inference.
            results = await asyncio.gather(
                perform(run_id, "review"), perform(run_id, "security")
            )
        elif stage not in {"execute_tests", "delivery"}:
            results = [await perform(run_id, stage)]
        else:
            results = []
        with Session() as db:
            run = db.scalar(select(Run).where(Run.id == run_id).with_for_update())
            project = db.get(Project, pid)
            if run.status != "running":
                return
            if stage in GATED:
                payload = results[0]["artifact"]
                propose(db, project, stage, payload, run.id)
                run.status = "awaiting_approval"
                project.project_status = "awaiting_approval"
            elif stage == "execute_tests":
                recipe = {"Python": "python", "JavaScript": "node", "Java": "java"}[
                    project.programming_language
                ]
                propose(
                    db,
                    project,
                    "test_execution",
                    {"recipe": recipe, "source_hash": source_hash(db, pid)},
                    run.id,
                )
                run.status = "awaiting_approval"
                project.project_status = "awaiting_approval"
            elif stage == "delivery":
                propose(
                    db,
                    project,
                    "delivery",
                    {
                        "source_hash": source_hash(db, pid),
                        "summary": "Review documentation, findings and actual test results before accepting delivery.",
                    },
                    run.id,
                )
                run.status = "awaiting_approval"
                project.project_status = "awaiting_approval"
            else:
                if stage == "quality":
                    for kind, result in zip(["review", "security"], results):
                        persist_findings(db, project, run, kind, result)
                        save_doc(db, project, kind, result["artifact"])
                elif stage == "security":
                    persist_findings(db, project, run, "security", results[0])
                    save_doc(db, project, "security", results[0]["artifact"])
                else:
                    save_doc(db, project, stage, results[0]["artifact"])
                run.stage += 1
                run.status = "queued"
                project.project_status = "working"
                if run.stage >= len(ROUTES[run.workflow_type]):
                    run.status = "completed"
                    project.project_status = "completed" if run.workflow_type == "quick_review" else "ready"
            run.lease_until = None
            run.updated_at = now()
            db.commit()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.warning("Workflow stage failed %s: %s", run_id, type(exc).__name__)
        with Session() as db:
            run = db.get(Run, run_id)
            if run and run.status not in {"cancelled", "completed"}:
                run.status = "failed"
                run.error = str(exc)[:800]
                run.lease_until = None
                db.get(Project, run.project_id).project_status = "needs_attention"
                event(
                    db,
                    run.project_id,
                    "workflow_failed",
                    {"run_id": run_id, "error": run.error},
                )
                db.commit()


async def dispatcher(stop):
    active = {}
    while not stop.is_set():
        try:
            for key, t in list(active.items()):
                if t.done():
                    try:
                        t.result()
                    except asyncio.CancelledError:
                        pass
                    active.pop(key)
            with Session() as db:
                for rid, running_task in active.items():
                    run = db.get(Run, rid)
                    if run and run.status == "cancelled":
                        # Also cancel a provider call waiting for the model semaphore.
                        # Otherwise an obsolete retry can consume the entire model budget.
                        running_task.cancel()
                    elif run and run.status == "running":
                        run.lease_until = now() + timedelta(seconds=60)
                cancelled_tasks = db.scalars(
                    select(AgentTask)
                    .join(Run, AgentTask.run_id == Run.id)
                    .where(
                        Run.status == "cancelled", AgentTask.task_status == "running"
                    )
                ).all()
                for cancelled_task in cancelled_tasks:
                    cancelled_task.task_status = "cancelled"
                    cancelled_task.completed_at = now()
                    for execution in db.scalars(
                        select(AgentExecution).where(
                            AgentExecution.agent_task_id == cancelled_task.id,
                            AgentExecution.execution_status == "running",
                        )
                    ):
                        execution.execution_status = "cancelled"
                        execution.execution_time = (
                            now() - execution.created_at
                        ).total_seconds()
                        execution.execution_logs = {"event": "workflow_cancelled"}
                stale = db.scalars(
                    select(Run).where(Run.status == "running", Run.lease_until < now())
                ).all()
                for r in stale:
                    r.status = "queued"
                    r.lease_until = None
                    tasks = db.scalars(
                        select(AgentTask).where(
                            AgentTask.run_id == r.id, AgentTask.task_status == "running"
                        )
                    ).all()
                    for t in tasks:
                        t.task_status = "interrupted"
                        for execution in db.scalars(
                            select(AgentExecution).where(
                                AgentExecution.agent_task_id == t.id,
                                AgentExecution.execution_status == "running",
                            )
                        ):
                            execution.execution_status = "interrupted"
                            execution.execution_time = (
                                now() - execution.created_at
                            ).total_seconds()
                            execution.execution_logs = {
                                "error": "Worker lease expired before an outcome was recorded"
                            }
                        t.error_message = (
                            "Worker lease expired; safe model work will be retried."
                        )
                    event(db, r.project_id, "workflow_recovered", {"run_id": r.id})
                if len(active) < 2:
                    run = db.scalar(
                        select(Run)
                        .where(Run.status == "queued")
                        .order_by(Run.created_at)
                        .with_for_update(skip_locked=True)
                        .limit(1)
                    )
                    if run:
                        if run.stage >= len(ROUTES[run.workflow_type]):
                            run.status = "completed"
                        else:
                            run.status = "running"
                            run.lease_until = now() + timedelta(seconds=60)
                            db.flush()
                            active[run.id] = asyncio.create_task(advance(run.id))
                db.commit()
        except Exception:
            log.exception("Dispatcher tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=2)
        except TimeoutError:
            pass
    for task in active.values():
        task.cancel()
    await asyncio.gather(*active.values(), return_exceptions=True)
