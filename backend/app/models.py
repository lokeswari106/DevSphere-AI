import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    CheckConstraint,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class User(Identity, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)


class Project(Identity, Base):
    __tablename__ = "projects"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    project_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    programming_language: Mapped[str] = mapped_column(String(30))
    framework: Mapped[str] = mapped_column(String(50))
    application_type: Mapped[str] = mapped_column(String(30), default="web_application")
    project_status: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )
    __table_args__ = (CheckConstraint("revision > 0"),)


class ProjectChild(Identity):
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)


class Requirement(ProjectChild, Base):
    __tablename__ = "project_requirements"
    requirement_type: Mapped[str] = mapped_column(String(40), default="srs")
    requirement_content: Mapped[dict] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("project_id", "requirement_type", "version"),
        CheckConstraint("version > 0"),
    )


class Run(ProjectChild, Base):
    __tablename__ = "workflow_runs"
    workflow_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    stage: Mapped[int] = mapped_column(Integer, default=0)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    request: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_hash: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str | None] = mapped_column(Text)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )
    __table_args__ = (
        Index(
            "one_active_run_per_project",
            "project_id",
            unique=True,
            postgresql_where=status.in_(
                ["queued", "running", "awaiting_approval", "testing"]
            ),
        ),
    )


class AgentTask(ProjectChild, Base):
    __tablename__ = "agent_tasks"
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(60))
    task_name: Mapped[str] = mapped_column(String(100))
    task_status: Mapped[str] = mapped_column(String(30), default="queued")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentExecution(ProjectChild, Base):
    __tablename__ = "agent_executions"
    agent_task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    execution_status: Mapped[str] = mapped_column(String(30))
    execution_logs: Mapped[dict] = mapped_column(JSONB, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    execution_time: Mapped[float] = mapped_column(Float, default=0)


class GeneratedFile(ProjectChild, Base):
    __tablename__ = "generated_files"
    file_name: Mapped[str] = mapped_column(String(180))
    file_path: Mapped[str] = mapped_column(String(240))
    file_content: Mapped[str] = mapped_column(Text)
    programming_language: Mapped[str] = mapped_column(String(30))
    version: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        UniqueConstraint("project_id", "file_path", "version"),
        CheckConstraint("version > 0"),
    )


class CodeReview(ProjectChild, Base):
    __tablename__ = "code_reviews"
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("generated_files.id"))
    file_path: Mapped[str] = mapped_column(String(240), default="")
    line_number: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20))
    issue_type: Mapped[str] = mapped_column(String(50))
    issue_description: Mapped[str] = mapped_column(Text)
    suggested_fix: Mapped[str] = mapped_column(Text)
    improved_code: Mapped[str] = mapped_column(Text, default="")
    evidence_status: Mapped[str] = mapped_column(String(40), default="ai_hypothesis")
    __table_args__ = (
        CheckConstraint("severity IN ('info','low','medium','high','critical')"),
    )


class TestResult(ProjectChild, Base):
    __tablename__ = "test_results"
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_runs.id"), index=True
    )
    test_type: Mapped[str] = mapped_column(String(40), default="sandbox")
    test_status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    source_hash: Mapped[str] = mapped_column(String(64))
    recipe: Mapped[str] = mapped_column(String(40))
    total_tests: Mapped[int | None] = mapped_column(Integer)
    passed_tests: Mapped[int | None] = mapped_column(Integer)
    failed_tests: Mapped[int | None] = mapped_column(Integer)
    execution_output: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict] = mapped_column(JSONB, default=dict)


class Document(ProjectChild, Base):
    __tablename__ = "project_documents"
    stale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    document_type: Mapped[str] = mapped_column(String(60))
    document_content: Mapped[dict] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        UniqueConstraint("project_id", "document_type", "version"),
        CheckConstraint("version > 0"),
    )


class ProjectVersion(ProjectChild, Base):
    __tablename__ = "project_versions"
    version_number: Mapped[int] = mapped_column(Integer)
    change_summary: Mapped[str] = mapped_column(Text)
    manifest: Mapped[dict] = mapped_column(JSONB, default=dict)
    __table_args__ = (UniqueConstraint("project_id", "version_number"),)


class Approval(ProjectChild, Base):
    __tablename__ = "approvals"
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_runs.id"), index=True
    )
    checkpoint: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    artifact_hash: Mapped[str] = mapped_column(String(64))
    base_revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSONB)
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(80))
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)
