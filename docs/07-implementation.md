# Implementation walkthrough and phase map

## Phase 1 — Requirements and architecture

`docs/01-architecture.md` records the architecture and boundaries. DevSphere is a modular monolith with React JavaScript, FastAPI, PostgreSQL and eight independently prompted Python agent modules. PostgreSQL doubles as a durable work queue; no Redis, Kubernetes, microservices or vector database is introduced. `docs/03-uml-handbook.md` explains all diagram families.

## Phase 2 — Database and FastAPI foundation

`app/config.py` reads environment configuration. `app/db.py` creates SQLAlchemy sessions. `app/models.py` defines thirteen tables, JSONB payloads, ownership foreign keys, version uniqueness and the active-run constraint. Alembic installs and upgrades the schema. `app/main.py` supplies health checks, error responses, security headers, OpenAPI and the compiled React application.

Run from `backend`: `.venv/bin/python -m alembic upgrade head`. Validate readiness through `/health/ready`. Data dictionary and SQL snapshot are in `docs/05-database.md` and `docs/database-schema.sql`.

## Phase 3 — Authentication and projects

`app/security.py` hashes passwords with Argon2, signs JWTs, checks CSRF/origin and rate limits selected operations. `api/routes.py` uses `owned()` before reading or changing a project. APIs hide another user's project with 404. Creating a project creates revision one; descriptions and language/framework combinations are validated. Deletion requires the exact project name and is a soft delete.

The role model is deliberately owner-only. There is no shared administrator bypass or team-invitation system. Tests cover registration, sessions, bearer authentication, CSRF, ownership and revision conflicts.

## Phase 4 — Specialized AI agents

`agents/orchestrator.py`, `requirements.py`, `architecture.py`, `database.py`, `code.py`, `review.py`, `security.py` and `testing_documentation.py` implement the eight responsibilities. Each uses a separate prompt and a Pydantic output schema. The last module has separate testing and documentation modes rather than pretending there are nine agents.

The provider adapter makes real HTTP calls to Ollama or OpenAI. Model output is validated; malformed output is an actual failed attempt. The database agent proposes typed endpoints; deterministic code compiles them into OpenAPI and validates the result. This avoids depending on a model to correctly escape an entire JSON document inside a JSON string. Generated Python is parsed for syntax without execution.

## Phase 5 — Orchestration and shared memory

`services/orchestration.py` chooses a dependency graph by workflow type, builds context from current approved documents and files, records tasks and attempts, and advances only after required outputs exist. Review and security run as independent tasks against the same source hash. The model provider semaphore can serialize inference on a small local machine without changing the dependency barrier.

Each result contains agent ID, task ID, status, artifact, usage and warnings. Original input/output and retry errors are persisted. Work is bounded by request timeouts, three attempts per task, at most two active run tasks per process and the source/context size limits. Leases make interrupted model work recoverable. Model-generated plans are artifacts; executable routing and permissions are controlled by trusted Python code.

## Phase 6 — Architecture, database and API generation

Architecture proposals contain editable Mermaid sources. The browser renders Mermaid with strict security and sanitized SVG. Invalid syntax falls back to source text and a visible error. Database proposals contain entities, keys, indexes and SQL text. Generated SQL is never applied to the DevSphere database. API contracts are compiled from typed model proposals, with path parameters declared required and OpenAPI validation before approval. Nested schemas and production authentication descriptions still require review.

## Phase 7 — Source files and versions

`services/artifacts.py` enforces normalized relative paths, text extensions, file-count and size bounds. A file change is stored as an approval payload first. Applying an approved change creates a new immutable version and project manifest. Hashes and revisions prevent stale approval. The code editor compares current and previous content; imports never write back to the source computer's original directory. This release supports additions and edits; deleting or renaming generated files is not yet a dedicated workflow.

## Phase 8 — Review, security and tests

Quality and security outputs are structured findings with file, optional line, severity, issue, suggested fix and improved code. Nonexistent file references are discarded and invalid line references are left unknown. AI findings remain hypotheses. The deterministic security pattern scanner flags selected unsafe constructs; it is not a comprehensive security scanner.

`services/sandbox.py` is used only by `scripts/run_sandbox_worker.py`. The API persists an approved test snapshot. The runner creates a disposable container with read-only root, no mounts, no network, non-root user, dropped capabilities, CPU/memory/PID/time limits and bounded output. It streams source into a temporary filesystem and runs a fixed Python, Node or Java recipe. Actual exit status and framework logs determine outcomes. No generated package-install commands execute. Failed tests trigger a repair checkpoint.

Run the platform checks from the root with `backend/.venv/bin/python -m pytest backend/tests -q`. `devsphere_test` is a separate database; live project data is not reset by the tests. Sandbox tests require the personal Docker context and built image.

## Phase 9 — React JavaScript interface

`frontend/src/main.jsx` implements authentication, dashboard, project creation and the eight workspace tabs. `api.js` manages same-origin requests and CSRF. `CodeEditor.jsx` bundles Monaco workers locally; `Diagram.jsx` renders Mermaid safely; `Artifacts.jsx` presents Markdown and typed output. `styles.css` provides the light/dark responsive layout. No TypeScript source is used.

Run `npm run dev --prefix frontend`; test with `npm test --prefix frontend`; compile with `npm run build --prefix frontend`. Firefox end-to-end tests use Playwright and an owned local demo account. They cover navigation, imports/approval, editing/comparison and mobile layout.

## Phase 10 — Integration

FastAPI serves the compiled frontend, so production browser requests use one origin. The workspace polls durable API state instead of relying on a browser connection to keep the workflow alive. Approval, regeneration, cancellation, context invalidation and test-result provenance cross module boundaries through PostgreSQL transactions. Markdown/PDF and source ZIP exports use only owned project artifacts.

The documentation agent receives the current source files, current instructions and recorded test outcomes. Historical design artifacts, old review advice and previous approval comments remain in project history but are excluded from its delivery context: they can describe code that has since changed. Each generated Markdown section is bounded to 2,500 characters. This avoids treating a conceptual architecture as the implemented design and keeps reports concise enough for the local model. Human delivery review is still required.

## Phase 11 — Testing, documentation and deployment

The source includes locked dependency files, Docker/Compose definitions, migration files, provider fault fixtures, unit/integration/sandbox/UI tests, setup scripts, UML source, screenshots and recorded demonstration evidence. `docs/08-testing.md` separates mocked provider tests from live Ollama results. `docs/09-deployment.md` distinguishes local execution, temporary free sharing and independently hosted deployment.

## Error handling and recovery

- Input and artifact failures return structured 422 responses; missing ownership returns 404.
- Simultaneous workflows, stale revisions and stale hashes return 409.
- Provider failures preserve attempt records and stop after the retry budget; no mock result is substituted.
- Worker failures leave visible failed/interrupted results. Rerunning code requires a fresh approval.
- Database writes are short transactions; model calls never hold a project row lock for their duration.
- Reports identify remaining risks and actual outcomes, not inferred performance claims.
