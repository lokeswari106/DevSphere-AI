import hashlib, json, re
from pathlib import PurePosixPath
from sqlalchemy import select, func
from fastapi import HTTPException
from app.config import settings
from app.models import (
    GeneratedFile,
    Document,
    ProjectVersion,
    Requirement,
    AuditEvent,
    Approval,
    now,
)

ALLOWED = {
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".md",
    ".txt",
    ".sql",
    ".java",
    ".css",
    ".html",
    ".yml",
    ".yaml",
    ".toml",
    ".xml",
    ".properties",
    ".csv",
    ".mmd",
    ".gitignore",
}


def digest(value):
    raw = (
        value
        if isinstance(value, str)
        else json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def safe_path(path):
    if (
        not isinstance(path, str)
        or len(path) > 240
        or "\\" in path
        or "\x00" in path
        or ":" in path
    ):
        raise ValueError("Unsafe file path")
    p = PurePosixPath(path)
    if (
        p.is_absolute()
        or ".." in p.parts
        or str(p) != path
        or any(x.startswith(".") and x != ".gitignore" for x in p.parts)
    ):
        raise ValueError(
            "Use normalized relative source paths without hidden directories"
        )
    if p.suffix.lower() not in ALLOWED and p.name not in {
        "requirements.txt",
        ".gitignore",
    }:
        raise ValueError("Unsupported source file type: " + path)
    if any(
        x in {"node_modules", "__pycache__", "target", "dist", "vendor"}
        for x in p.parts
    ):
        raise ValueError("Upload source files, not build/dependency directories")
    return path


def validate_files(files):
    cfg = settings()
    if not files or len(files) > cfg.max_files:
        raise ValueError("File count limit exceeded")
    paths = set()
    total = 0
    for item in files:
        path = safe_path(item["path"])
        body = item["content"]
        if path.casefold() in paths:
            raise ValueError("Duplicate or case-conflicting path: " + path)
        paths.add(path.casefold())
        if "\x00" in body:
            raise ValueError("Binary content is not accepted")
        size = len(body.encode())
        total += size
        if size > cfg.max_file_bytes:
            raise ValueError("File too large: " + path)
        if re.search(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|sk-proj-)[A-Za-z0-9_-]{20,}",
            body,
        ):
            raise ValueError(
                "Potential private key or access token detected; remove credentials before uploading"
            )
    if total > cfg.max_project_bytes:
        raise ValueError("Project source limit exceeded")


def latest_files(db, pid):
    rows = db.scalars(
        select(GeneratedFile)
        .where(GeneratedFile.project_id == pid)
        .order_by(GeneratedFile.file_path, GeneratedFile.version.desc())
    ).all()
    seen = set()
    result = []
    for row in rows:
        if row.file_path not in seen:
            seen.add(row.file_path)
            result.append(row)
    return result


def file_payload(db, pid):
    return [
        {"path": f.file_path, "content": f.file_content} for f in latest_files(db, pid)
    ]


def source_hash(db, pid):
    return digest(file_payload(db, pid))


def latest_docs(db, pid):
    rows = db.scalars(
        select(Document)
        .where(Document.project_id == pid, Document.stale.is_(False))
        .order_by(Document.document_type, Document.version.desc())
    ).all()
    result = {}
    for r in rows:
        if r.document_type not in result:
            result[r.document_type] = r
    return result


def save_doc(db, project, kind, payload):
    version = (
        db.scalar(
            select(func.max(Document.version)).where(
                Document.project_id == project.id, Document.document_type == kind
            )
        )
        or 0
    ) + 1
    row = Document(
        project_id=project.id,
        document_type=kind,
        document_content=payload,
        version=version,
        content_hash=digest(payload),
    )
    db.add(row)
    if kind == "requirements":
        db.add(
            Requirement(
                project_id=project.id,
                requirement_type="srs",
                requirement_content=payload,
                version=version,
            )
        )
    return row


def bump_version(db, project, summary):
    project.revision += 1
    project.updated_at = now()
    db.flush()
    db.add(
        ProjectVersion(
            project_id=project.id,
            version_number=project.revision,
            change_summary=summary,
            manifest={
                f.file_path: f.content_hash for f in latest_files(db, project.id)
            },
        )
    )


def apply_files(db, project, files):
    validate_files(files)
    existing = {f.file_path: f for f in latest_files(db, project.id)}
    merged = {k: {"path": k, "content": v.file_content} for k, v in existing.items()}
    merged.update({f["path"]: f for f in files})
    validate_files(list(merged.values()))
    for f in files:
        old = existing.get(f["path"])
        sha = digest(f["content"])
        if old and old.content_hash == sha:
            continue
        db.add(
            GeneratedFile(
                project_id=project.id,
                file_name=PurePosixPath(f["path"]).name,
                file_path=f["path"],
                file_content=f["content"],
                programming_language=PurePosixPath(f["path"]).suffix.lstrip("."),
                version=old.version + 1 if old else 1,
                content_hash=sha,
            )
        )
    db.flush()


def propose(db, project, checkpoint, payload, run_id=None):
    a = Approval(
        project_id=project.id,
        run_id=run_id,
        checkpoint=checkpoint,
        artifact_hash=digest(payload),
        base_revision=project.revision,
        payload=payload,
    )
    db.add(a)
    db.flush()
    event(
        db,
        project.id,
        "approval_requested",
        {"approval_id": a.id, "checkpoint": checkpoint, "hash": a.artifact_hash},
    )
    return a


def event(db, pid, kind, data, user_id=None):
    db.add(
        AuditEvent(project_id=pid, user_id=user_id, event_type=kind, event_data=data)
    )


def owned(db, pid, user, lock=False):
    from app.models import Project

    stmt = select(Project).where(
        Project.id == pid, Project.user_id == user.id, Project.deleted.is_(False)
    )
    if lock:
        stmt = stmt.with_for_update()
    p = db.scalar(stmt)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


def invalidate(db, project, kind):
    affected = {
        "brief": {
            "plan",
            "requirements",
            "architecture",
            "database",
            "review",
            "security",
            "documentation",
        },
        "requirements": {
            "architecture",
            "database",
            "review",
            "security",
            "documentation",
        },
        "architecture": {"database", "review", "security", "documentation"},
        "database": {"review", "security", "documentation"},
        "code": {"review", "security", "documentation"},
        "tests": {"documentation"},
    }.get(kind, set())
    for d in db.scalars(
        select(Document).where(
            Document.project_id == project.id, Document.document_type.in_(affected)
        )
    ):
        d.stale = True
