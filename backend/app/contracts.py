"""Response contracts derived from the same mapped columns persisted in PostgreSQL."""

from typing import Any
from pydantic import BaseModel, create_model
from app import models


def record(model, exclude=()):
    fields = {}
    for c in model.__table__.columns:
        if c.name in exclude:
            continue
        typ = c.type.python_type
        fields[c.name] = (typ | None if c.nullable else typ, ...)
    return create_model(model.__name__ + "Response", **fields)


UserResponse = record(models.User, ("password_hash",))
ProjectResponse = record(models.Project)
FileResponse = record(models.GeneratedFile)
ApprovalResponse = record(models.Approval)
DocumentResponse = record(models.Document)
RequirementResponse = record(models.Requirement)
VersionResponse = record(models.ProjectVersion)
EventResponse = record(models.AuditEvent)
ReviewResponse = create_model(
    "ReviewResponse", source_current=(bool, ...), __base__=record(models.CodeReview)
)
TestResponse = create_model(
    "TestResponse", source_current=(bool, ...), __base__=record(models.TestResult)
)
RunResponse = create_model(
    "RunResponse", stages=(list[str], ...), __base__=record(models.Run)
)
TaskResponse = record(models.AgentTask, ("input_data",))
ExecutionResponse = record(models.AgentExecution)
DetailedTaskResponse = create_model(
    "DetailedTaskResponse",
    executions=(list[ExecutionResponse], ...),
    __base__=record(models.AgentTask),
)


class AuthResponse(BaseModel):
    user: UserResponse
    csrf_token: str
    access_token: str
    token_type: str


class MeResponse(BaseModel):
    user: UserResponse
    csrf_token: str


class StartResponse(BaseModel):
    run_id: str
    status: str
    status_url: str | None = None


class StatusResponse(BaseModel):
    status: str
    revision: int | None = None


class WorkflowResponse(BaseModel):
    run: RunResponse | None
    tasks: list[TaskResponse]
    approvals: list[ApprovalResponse]


class DiffResponse(BaseModel):
    before: str
    after: str
    diff: str


class SettingsResponse(BaseModel):
    provider: str
    model: str
    models: list[str]
    runner_online: bool
    sandbox_enabled: bool
    runner_capabilities: dict[str, Any]
    registration_enabled: bool
    max_files: int
    max_project_bytes: int
    version: str
