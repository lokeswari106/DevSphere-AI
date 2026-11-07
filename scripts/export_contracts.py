"""Export contracts and the PostgreSQL schema from the running source definitions."""

import sys, json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.main import app
from app.db import Base
from app import models, schemas
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql
from openapi_spec_validator import validate

spec = app.openapi()
validate(spec)
(root / "docs/openapi.json").write_text(json.dumps(spec, indent=2))
(root / "docs/database-schema.sql").write_text(
    "-- Generated from SQLAlchemy metadata. Use Alembic migrations for installation.\n\n"
    + "\n\n".join(
        str(CreateTable(t).compile(dialect=postgresql.dialect()))
        + ";\n"
        + "\n".join(
            str(CreateIndex(i).compile(dialect=postgresql.dialect())) + ";"
            for i in t.indexes
        )
        for t in Base.metadata.sorted_tables
    )
)
text = "# PostgreSQL data dictionary\n\nPersistent JSON payloads use JSONB. UUID-format identifiers are stored as varchar(36). Timestamps include a timezone. Python supplies ID and timestamp defaults. The migration files are the installation authority.\n\n"
for t in Base.metadata.sorted_tables:
    text += (
        "## "
        + t.name
        + "\n\n| Column | SQL type | Nullable | Constraint/reference |\n| --- | --- | --- | --- |\n"
    )
    for c in t.columns:
        constraints = (
            ("Primary key; " if c.primary_key else "")
            + ("Unique; " if c.unique else "")
            + ", ".join(str(k.target_fullname) for k in c.foreign_keys)
        )
        text += f"| {c.name} | {c.type.compile(dialect=postgresql.dialect())} | {'Yes' if c.nullable else 'No'} | {constraints or '-'} |\n"
    text += (
        "\nIndexes and constraints: "
        + ", ".join(
            str(c.name or c.__class__.__name__)
            for c in list(t.indexes) + list(t.constraints)
        )
        + ".\n\n"
    )
text += "## Transaction rules\n\nOnly one active workflow may exist per project; PostgreSQL enforces a partial unique index. API writes lock the owned project before checking its revision. Approvals additionally lock the proposal and bind its artifact hash. Immutable file/document versions use composite uniqueness constraints. Cross-project operations first check ownership and return 404 for a resource the user does not own. This release uses service-level ownership checks rather than PostgreSQL row-level security.\n"
(root / "docs/05-database.md").write_text(text)
text = "# API contracts\n\nInteractive Swagger: http://localhost:8010/docs. Complete OpenAPI 3.1 document: [openapi.json](openapi.json). Request and response fields are generated from Pydantic contracts and mapped record definitions.\n\n## Authentication\n\nRegister/login returns an HttpOnly SameSite=Strict cookie, an access token for API clients and a CSRF value. The React client keeps the CSRF value in memory and sends X-CSRF-Token on cookie-authenticated writes. API clients may use Authorization: Bearer TOKEN. Never place a token in a URL. `/api/auth/me` restores the browser session. Tokens expire after eight hours; refresh-token rotation is not included. Logout clears the browser cookie and does not revoke an already copied bearer token.\n\n## Common responses\n\n201 creates a resource; 202 queues work or proposes a change; 204 returns no body. Errors use code, message, optional details and request_id. 401 requires login, 403 rejects CSRF/origin, 404 hides unowned resources, 409 signals stale revisions or unmet dependencies, 422 signals invalid data and 429 rate limits requests. Results use project ownership checks on every protected route.\n\n## Endpoints\n\n| Method | Path | Responsibility |\n| --- | --- | --- |\n"
for path, ops in spec["paths"].items():
    for method, operation in ops.items():
        if method not in ["get", "post", "put", "delete"]:
            continue
        text += f"| {method.upper()} | `{path}` | {operation.get('summary', '')} |\n"
text += """\n## Approval protocol

1. GET workflow or approvals; read the pending artifact, `artifact_hash` and `base_revision`.
2. Inspect the complete artifact. PUT approval may edit eligible structured artifacts and returns a new hash.
3. POST decision with `decision`, `artifact_hash`, `expected_revision` and optional `comment`.
4. A matching hash/revision commits the artifact or queues approved execution. A stale request returns 409 and must be reviewed again.

```json
{"decision":"approve","artifact_hash":"<64-character proposal SHA-256>","expected_revision":3,"comment":"Reviewed design and limitations"}
```

## Polling and idempotency

Poll workflow/status about every three seconds while active. Starting a second active run returns 409. Repeating an already resolved approval returns 409 rather than applying it twice. A request-ID header correlates errors; no generic Idempotency-Key implementation is claimed. A disconnected browser can reload the stored run and artifacts.

## Input boundaries

Project descriptions are limited to 12,000 characters. File proposals support at most 60 files, 100 KB per file and 750 KB combined source. Text source only; archives, executable binaries, absolute paths, traversal, hidden credential files and common private-key/token patterns are rejected. Projects larger than the configured model context budget stop explicitly rather than silently dropping a source file.
"""
(root / "docs/06-api-contracts.md").write_text(text)
out = root / "docs/agent-contracts"
out.mkdir(exist_ok=True)
for name in [
    "Plan",
    "SRS",
    "Architecture",
    "DatabaseDesign",
    "DatabaseDraft",
    "CodeBundle",
    "Review",
    "Delivery",
]:
    (out / (name + ".json")).write_text(
        json.dumps(getattr(schemas, name).model_json_schema(), indent=2)
    )
print(
    f"Exported {len(spec['paths'])} OpenAPI paths and {len(Base.metadata.tables)} PostgreSQL tables."
)
