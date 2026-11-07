# DevSphere AI architecture and technical design

DevSphere AI is an intelligent software engineering workspace for a final-year college demonstration. It coordinates eight specialized agents, keeps each project's context in PostgreSQL, proposes versioned artifacts and asks a person to approve consequential transitions. This design uses a modular monolith. Its product is a reviewable engineering project, not a promise that arbitrary generated software is production-ready.

The user approved all implementation phases on 7 November 2026. Application approval checkpoints remain part of the product. DevSphere AI is a separate project from AgentSphere and the Java courses. No existing repository or office account is part of its design.

## Architecture decisions

The React JavaScript application is compiled by Vite and served with the FastAPI application from one origin. React Router manages screens; Axios handles API calls; Monaco provides editing and diffs; Mermaid renders architecture diagrams. A quiet sidebar, a project list and eight workspace tabs keep the interface approachable. Detailed agent outputs are expandable rather than scattered across dashboard widgets.

FastAPI modules separate authentication, projects, workflow execution, artifacts, review, testing and exports. SQLAlchemy and Alembic manage PostgreSQL. A durable workflow row and task rows are the source of truth. A bounded asynchronous dispatcher performs model calls outside request handling. Status polling avoids a WebSocket service and recovers naturally after navigation. There is no Redis, vector database, Kubernetes or distributed microservice layer.

A provider interface offers local Ollama and optional OpenAI Responses API integration. Agent-specific system prompts, schema validation and deterministic policy checks surround every model response. No model response directly runs a command or writes an existing source tree. Files are database artifacts until approved and exported.

A separate runner process claims only approved test jobs. Its Docker context is explicitly configured and belongs to this project. It launches disposable, non-root, network-disabled containers with CPU, memory, process, filesystem and wall-time limits. The API process has no Docker socket or execution privileges. The runner receives a versioned source snapshot; neither database credentials nor model keys enter test containers. The runner controller is trusted; generated files, tests, dependency manifests and model output are untrusted.

## Component responsibilities

| Component | Responsibility | Boundary |
|---|---|---|
| Browser | Forms, timeline, diagrams, editor, diffs and downloads | Never contains model secrets or executes generated applications |
| FastAPI routes | Validate requests, verify identity and project ownership | Return structured errors and asynchronous job references |
| Orchestrator | Select tasks, enforce dependencies, pause for approvals and recover work | Never treats model instructions as authorization |
| Agent modules | Produce typed requirements, designs, code, findings and documentation | Read immutable context snapshots; return structured results |
| Artifact service | Version files and documents; compare and approve changes | Atomic application of a proposal against a base hash |
| PostgreSQL | Users, artifacts, approvals, execution history and job state | All project queries scoped to owner; transactions protect transitions |
| Model adapter | Timeouts, bounded retries, structured output and usage records | Provider configurable; no fallback to fictional outputs |
| Runner controller | Claim approved test snapshots and enforce fixed recipes | Separate process; never execute user code on the host |
| Sandbox container | Run a fixed Python, Node or Java test recipe | No network, host source mounts, secrets or Docker socket |

## Eight agents and their contracts

| Agent | Inputs | Outputs and validation |
|---|---|---|
| Engineering Orchestrator | User intent, workflow type, current approved artifacts, constraints | Typed plan, milestones and dependencies; deterministic routing restricts valid tasks |
| Requirement Intelligence | Natural-language requirement and prior decisions | Functional/non-functional requirements, stories, acceptance criteria, complexity and open questions |
| System Architecture | Approved SRS and language/framework constraints | Components, architecture style, patterns, trade-offs and Mermaid diagrams |
| Database and API Design | Approved requirements and architecture | Entities, keys, indexes, SQL migrations and an OpenAPI document; validate format before publication |
| Intelligent Code Generation | Approved SRS, design, API contracts and current file manifest | File proposals and implementation explanation; validate paths, sizes, duplicate names and supported languages |
| Code Review and Quality | Exact candidate file snapshot and acceptance criteria | File/line findings, severity, rationale, suggested fix and improved example |
| Bug Detection and Security | Same code snapshot and dependency metadata | AI hypotheses plus separately labelled deterministic observations; never label an AI suspicion a verified exploit |
| Testing and Documentation | Candidate source, requirements, review results and actual runner results | Test-file proposals and technical documents; test totals come only from execution, not from the LLM |

Testing and documentation are two modes of the same eighth agent, not a ninth agent. The orchestrator also performs a real planning model call; its scheduler and policy decisions remain deterministic.

Every agent context contains project ID, run ID, task ID, original requirement, assignment, selected language/framework, approved artifact references, previous relevant outputs, source snapshot hash and resource constraints. Every result records agent ID, task ID, status, summary, typed artifact, warnings, evidence references, confidence where meaningful, provider/model and observed token usage. Confidence is a heuristic, not a quality guarantee. Invalid JSON, refusals and provider errors remain visible.

## Conditional workflow and approvals

The full workflow is planning, requirements, requirement approval, architecture, architecture approval, database/API design, database approval, source generation, code approval, parallel review and security, test generation, test-file approval, test-execution approval, actual tests, documentation and final delivery approval. No downstream agent reads an unapproved predecessor where approval is required.

Review-only selects planning, quality review, security and documentation. Documentation-only uses approved source and prior outputs. A targeted regeneration starts at the selected artifact and invalidates dependent approvals. A failed test result allows a bounded repair proposal followed by code approval, re-review and new test-execution approval. Failure must not be silently converted to success. A user can instead accept delivery with disclosed failures; the report and run status must distinguish completion from tests passing.

Approvals bind to an immutable artifact or test snapshot hash and the expected project revision. Changing a file or design makes an old approval stale. Approve, reject and request changes are separate decisions. User edits produce a new proposal/version, never erase old content. Uploaded files are imported into a new project snapshot and are not written back into an external repository.

## Persistent orchestration and failure behavior

Create the workflow and initial tasks in one transaction before returning HTTP 202. Allow one active workflow per project. Claim runnable work with a PostgreSQL row lock, persist attempts before invoking a provider, then validate and save output atomically. Keep lease/heartbeat timestamps for restart recovery. A restart may repeat a side-effect-free model call but must not apply a file proposal twice. Record retries and interrupted attempts. Test jobs require a new dispatch lease; ambiguous interrupted execution is shown as interrupted and cannot be reported as passed.

The dependency barrier waits for both review and security results. A shared source hash makes their outputs comparable. Limits include one active run per project, bounded model concurrency, up to two retries per task, a bounded artifact size and at most one repair cycle per explicit repair request. Rate limits, task timeouts and run budgets are configuration, not model-controlled values.

## Database schema

All IDs are UUIDs and timestamps are UTC. JSONB holds typed results, never replaces ownership or foreign keys. The ten requested tables are retained and supplemented with workflow_runs, approvals and audit_events to represent resumable execution and auditable human decisions.

| Table | Principal fields and relationships |
|---|---|
| users | id PK, name, normalized unique email, password_hash, created_at |
| projects | id PK, user_id FK users, project_name, description, programming_language, framework, application_type, project_status, revision, created_at, updated_at |
| project_requirements | id PK, project_id FK, requirement_type, requirement_content JSONB, version, created_at; unique project/type/version |
| workflow_runs | id PK, project_id FK, workflow_type, status, stage, context JSONB, request JSONB, source_hash, lease_until, created_at, updated_at |
| agent_tasks | id PK, project_id FK, run_id FK, agent_name, task_name, task_status, priority, input_data JSONB, output_data JSONB, error_message, started_at, completed_at |
| agent_executions | id PK, project_id FK, agent_task_id FK, execution_status, execution_logs JSONB, retry_count, execution_time, created_at |
| generated_files | id PK, project_id FK, file_name, file_path, file_content, programming_language, version, content_hash, created_at; unique project/path/version |
| code_reviews | id PK, project_id FK, run_id FK, file_id FK nullable, file_path, line_number nullable, severity, issue_type, issue_description, suggested_fix, evidence_status, created_at |
| test_results | id PK, project_id FK, run_id FK, test_type, test_status, source_hash, recipe, total_tests nullable, passed_tests nullable, failed_tests nullable, execution_output, details JSONB, created_at |
| project_documents | id PK, project_id FK, document_type, document_content JSONB, version, content_hash, created_at; unique project/type/version |
| project_versions | id PK, project_id FK, version_number, change_summary, manifest JSONB, created_at; unique project/version |
| approvals | id PK, project_id FK, run_id FK nullable, checkpoint, status, artifact_hash, base_revision, payload JSONB, comment, decided_by FK users nullable, created_at, decided_at |
| audit_events | id PK, project_id FK nullable, user_id FK nullable, event_type, event_data JSONB, created_at |

Index owner/project creation order, task/run status, pending approval/project, file project/path/version and test run/time. Check positive versions, known statuses, nonnegative counts and valid severity. Use a partial unique index for active project workflows. Never cascade-delete execution evidence while a run is active. Project deletion is an explicit confirmed soft deletion, keeping recovery possible. No password hash appears in API schemas.

## API contract conventions

FastAPI publishes /docs and /openapi.json. Identity uses short-lived JWT authentication. Browser requests use an HttpOnly same-site cookie and CSRF protection for mutations; an explicit bearer token supports API clients. Project ownership is checked for every nested resource. Cross-owner IDs return 404. Error bodies contain code, message, request_id and safe details. Validation returns 422, stale state 409, missing approval 409, unsupported runner 503, rate limit 429 and unavailable model 502/503 through task status.

Collection routes are bounded. Mutations that enqueue work return HTTP 202 with run or approval identifiers and a status URL. Use expected_revision and exact artifact hashes for approvals and file edits. Clients poll active work at two seconds, back off on failures and stop when idle. Downloads are authenticated and include explicit filenames.

| Route group | Contracts |
|---|---|
| Auth | POST /api/auth/register {name,email,password}; POST /login; GET /me; POST /logout |
| Projects | POST and GET /api/projects; GET, PUT and DELETE /api/projects/{id}; DELETE requires project name confirmation |
| Requirements | POST and GET /api/projects/{id}/requirements; creates a versioned proposal |
| Workflows | POST /execute {workflow_type,instructions}; GET /workflow, /status, /agents and /agent-tasks; POST /cancel and /retry |
| Design | POST /design and /database-design; require approved prerequisite versions |
| Files | POST /generate-code; GET /files and /files/{file_id}; PUT /files/{file_id} {content,expected_revision}; proposal first |
| Imports | POST /files/import with a bounded file list; reject unsafe paths and binary payloads |
| Review | POST /review and /security-analysis; GET /reviews |
| Tests | POST /generate-tests and /run-tests; GET /tests; execution requires a hash-bound approval |
| Documents | POST /documentation; GET /documents; GET /documents/{id}/download?format=md or pdf |
| History | GET /versions; GET /files/{id}/diff?against={version}; GET /events |
| Approvals | GET /approvals; POST /approvals/{id}/decision {decision,artifact_hash,expected_revision,comment} |
| Exports | GET /export for ZIP of approved files and current documentation |
| System | GET /health/live and /health/ready; GET /api/settings for safe capabilities |

Concrete request/response schemas are maintained in the generated OpenAPI contract after implementation. This table is the Phase 1 intent; any final deviations must be documented alongside the implemented contract.

## Frontend wireframe and interaction model

Desktop layout has a narrow left sidebar and one main content column. The dashboard opens with "What would you like to build?", one Create project action and a recent-project list. New Project asks for name, requirement, language, framework and application type. A visible model label and capability status explain whether generation and testing are available.

The workspace header shows project name, one status, selected stack and a primary next action. The eight tabs are Overview, Requirements, Architecture, Database and APIs, Code, Code Review, Testing and Documentation. The Overview includes an agent timeline and a compact history list. Approval controls appear beside the exact artifact being approved. Code has a file tree, Monaco editor and before/after diff. Review shows severity filters and source references. Testing shows a real execution log and clearly distinguishes not run, queued, passed, failed, timed out and unavailable. Documentation supports Markdown/PDF and ZIP exports.

Mobile stacks the sidebar into a menu and keeps tabs horizontally scrollable. Keyboard focus, labelled inputs, readable contrast, loading/empty/error states and confirmation of destructive actions are part of acceptance. Mermaid is rendered in strict mode, sanitized, with a source fallback when invalid. Generated HTML is displayed as source, never executed in the workspace.

## Planned folder structure

```
DevSphereAI/
  backend/app/{api,agents,services}/
  backend/app/{main,config,db,models,schemas,security}.py
  backend/migrations/versions/
  backend/tests/
  frontend/src/{components,pages}/
  frontend/tests/
  sandbox/                  # trusted runner images and fixed recipes
  scripts/                  # setup, runner, live demo and packaging
  docs/                     # phase guides and college report
  diagrams/                 # editable UML and rendered diagrams
  contracts/                # implemented OpenAPI and agent schemas
  samples/                  # labelled demonstration inputs and results
  compose.yaml
  .env.example
```

## Security design

Hash passwords with Argon2; protect signing and provider keys in ignored environment files. Validate origin and CSRF for cookie-authenticated writes. Apply per-IP authentication and per-user job limits. Do not store secrets in source examples, reports or logs. Validate UTF-8 file content, normalized relative paths, filename allowlists, size/count limits and ZIP expansion limits; never follow symlinks or accept .env/private key uploads. Use SQLAlchemy parameterization, ownership checks and optimistic revisions.

Prompt injection defenses use trusted system prompts, explicit untrusted context delimiters and schema validation. Uploaded comments and generated docs cannot approve actions or change tool privileges. Review proposals as hypotheses. Dependency scanning reports package data and advisory limitations; never claim an unqueried package is safe.

Sandbox isolation is defense in depth, not a proof against kernel exploits. The college demonstration uses a dedicated personal Linux VM/Docker context and disposable containers. Disable the runner for public hostile multi-tenant workloads until a stronger independently operated isolation service is available. Curated dependencies are prepared by trusted setup, and test execution has no network or arbitrary package installation. Missing dependencies produce an honest failure.

## Free deployment and operating guide

The complete zero-subscription demonstration runs locally with PostgreSQL, Ollama, FastAPI/React and the dedicated sandbox. A Cloudflare Quick Tunnel can provide a temporary HTTPS app URL while this computer is awake. Only the app port is exposed; the model, database and Docker endpoint stay private. Registration can be available locally and restricted on a public demo. A public URL is not permanent hosting.

Render's free web service sleeps after inactivity and loses local filesystem changes; its free PostgreSQL expires after 30 days. Neon offers a separately limited free PostgreSQL plan. An optional cloud API/UI can use Neon, but inference and a safe runner still need reachable resources. No paid service or always-on free guarantee is assumed. This release therefore prioritizes a complete local demonstration and temporary free deployment. Current sources are listed in references; recheck quotas before deployment.

## Implementation roadmap and acceptance

1. Phase 1 establishes the architecture, contracts, schema, wireframe and UML catalogue.
2. Phase 2 creates PostgreSQL persistence, migrations, configuration, health checks and transaction boundaries.
3. Phase 3 adds JWT auth, CSRF, ownership, project creation/edit/history and deletion confirmation.
4. Phase 4 implements all eight agent modules and actual model adapters with typed output validation.
5. Phase 5 adds durable scheduling, shared context, dependency barriers, retries and approval decisions.
6. Phase 6 produces requirements, Mermaid architecture, database artifacts and OpenAPI documents.
7. Phase 7 adds source proposals, approval, immutable versions, imports, editor diffs and ZIP exports.
8. Phase 8 implements quality/security review, test generation, a separate sandbox runner and actual test results.
9. Phase 9 builds and tests the simple React JavaScript workspace and responsive screens.
10. Phase 10 integrates local services, exercises live model workflows and records outcomes honestly.
11. Phase 11 completes automated checks, Docker deployment files, UML/college documentation and the running local demonstration.

## Demonstration acceptance scenarios

The e-commerce scenario must produce requirements through documentation for a bounded application. Payment integration must use a clearly labelled test-provider boundary, never real charges. URL Shortener must include creation, redirect, validation and collision behavior, plus actual tests. Existing-code analysis imports a small Node project and runs only relevant review/security/documentation agents. Live outputs come from the configured model; automated fixtures remain under tests. Each demonstration report records provider/model, timestamps, task outcomes and actual test status. No performance, coverage or security success metric is invented.

## UML catalogue and references

The documentation pack will include all fourteen UML diagram families: class, object, component, composite structure, package, deployment, profile, use case, activity, state machine, sequence, communication, interaction overview and timing. ER diagrams, workflow and UI wireframes supplement UML. Mermaid is used for supported forms; clearly labelled equivalent views and editable PlantUML are used where formal UML notation is needed.

Primary documentation checked 7 November 2026: [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/), [PostgreSQL locking](https://www.postgresql.org/docs/current/sql-select.html), [SQLAlchemy versioning](https://docs.sqlalchemy.org/en/20/orm/versioning.html), [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs), [Ollama structured output](https://docs.ollama.com/capabilities/structured-outputs), [Docker runtime controls](https://docs.docker.com/reference/cli/docker/container/run/), [Docker rootless mode](https://docs.docker.com/engine/security/rootless/), [Mermaid configuration](https://mermaid.js.org/config/usage.html), [Render free plans](https://render.com/docs/free), [Neon free plan](https://neon.com/pricing), [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
