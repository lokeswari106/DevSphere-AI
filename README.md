# DevSphere AI

**Intelligent Software Engineering Assistant** — a final-year project with React JavaScript, FastAPI, PostgreSQL and eight specialized AI agents.

A requirement becomes an inspectable plan, SRS, architecture, API/schema design, source proposal, quality/security review, actual sandbox test result and technical report. Human approvals bind the artifact hash and project revision. The platform retains prior files and decisions.

## Start here

Install **Python 3.12** and **Docker Desktop** (or personal Docker Engine with Compose). Download this repository using **Code → Download ZIP**, or run:

```sh
git clone https://github.com/lokeswari106/DevSphere-AI.git
cd DevSphere-AI
```

Open a terminal in the project folder, then run:

```sh
python3.12 devsphere.py
```

Windows PowerShell: `py -3.12 devsphere.py`.

The launcher prepares the app, PostgreSQL, local AI model and isolated test runner. Open **http://localhost:8010**, create your account, and keep the terminal open. **Ctrl+C** stops the stack without deleting projects; the same command starts it again. No invitation token is required.

Follow **[RUN_LOCALLY.md — required installations and step-by-step setup on another computer](RUN_LOCALLY.md)** for prerequisite checks, Windows/macOS/Linux commands, first-time downloads, memory requirements, stopping, restarting and troubleshooting. The [advanced setup guide](docs/02-local-setup.md) retains native installation and manual Docker instructions. Existing native installations can continue with `backend/.venv/bin/python scripts/start_local.py`.

## What is implemented

- Eight separately prompted Python agents using real structured Ollama responses; optional OpenAI adapter.
- Conditional generation/review/security/design/testing/documentation/repair workflows.
- Persistent shared context, execution history, retry limits and lease recovery.
- Plan, requirements, architecture, database, source, test execution and delivery checkpoints.
- Editable proposals, immutable file versions, comparisons, imports and ZIP exports.
- Mermaid diagrams, Monaco code editor, severity-filtered findings and actual test logs.
- Separate constrained Docker execution for Python, Node and Java tests.
- Markdown/PDF project reports, responsive light/dark interface and owner-scoped accounts.

This is a working educational platform. AI-generated software requires review, and model quality varies. The live app never substitutes mock outputs for a failed model call. Tests and coverage are never reported as passing without recorded execution. Richer nested API schemas, public multi-tenant hardening and comprehensive dependency scanning remain extension work.

## Source map

```text
backend/
  app/agents/           eight specialized agent modules
  app/api/              REST endpoints and approval actions
  app/services/         orchestration, artifacts, providers, sandbox, exports
  app/models.py         PostgreSQL tables
  app/schemas.py        input and agent contracts
  app/contracts.py      API response contracts
  migrations/           Alembic schema versions
  tests/                unit, API, database, orchestration and sandbox tests
frontend/
  src/                  React JavaScript interface and components
  tests/                Vitest and Playwright Firefox checks
sandbox/                reviewed container image and fixed test harness
scripts/                setup, run, contracts, documentation and demo helpers
docs/                   architecture, setup, API, UML, testing and deployment
samples/                labelled inputs and saved real demonstration exports
output/                 final Word/PDF documents and source archive
postman/                provider fault simulation (automated tests only)
Dockerfile              single application image
compose.yaml            application + PostgreSQL, optional Ollama
.env.example            configuration names, no real secrets
```

## Documentation

- [Architecture and design](docs/01-architecture.md)
- [Run on another computer](docs/02-local-setup.md)
- [All UML diagrams and workflow](docs/03-uml-handbook.md)
- [Step-by-step user guide](docs/04-user-guide.md)
- [Database dictionary](docs/05-database.md) and [schema SQL](docs/database-schema.sql)
- [API contracts](docs/06-api-contracts.md) and [OpenAPI](docs/openapi.json)
- [All eleven implementation phases](docs/07-implementation.md)
- [Testing and actual results](docs/08-testing.md)
- [Free demo/deployment instructions](docs/09-deployment.md)
- [College project report](docs/10-final-project-report.md)
- [Diagram, completion status and theme fixes](docs/11-ui-fixes.md)
- [Visual style and color guide](docs/12-visual-style.md)
- [Paste/upload code review and e-commerce repair](docs/13-reviews-and-test-repair.md)

## Verification

Use the separate PostgreSQL `devsphere_test` database and build the sandbox first:

```sh
backend/.venv/bin/python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
npm run test:e2e --prefix frontend
```

End-to-end checks expect the locally generated `.local/demo-account.json`; run `backend/.venv/bin/python scripts/demo_session.py` once against your local server to create an owned demonstration account and three projects. Its credentials stay private. Playwright Firefox may need `npx playwright install firefox` from the frontend folder.

The provider simulation and its four fault checks are described in the testing guide. Automated fixtures are never used for the live demo.

Recorded validation: **57 backend checks, 26 frontend unit/component checks and 11 Firefox end-to-end checks passed**. Separately, the reviewed URL Shortener passed 5 sandbox tests and E-commerce Studio passed 7. All three saved demonstration projects completed their final approval. See [live evidence and presentation steps](samples/live/README.md), [actual run records](samples/live/status.json), and [local/public access checks](docs/run-verification.json). The evidence preserves model failures, cancelled attempts and human corrections; it does not claim unattended generation or production readiness.

The user's separate **E-commerce application** has now been repaired and passed **24 sandbox tests**. Paste/upload code review produced replacement suggestions through real model calls. The portable launcher also passed a stop/restart check that retained its account, source, test result and review history. See [repair evidence](docs/review-repair-verification.json) and [portable startup evidence](docs/portable-verification.json).

## Free presentation

Native Ollama does not require a paid model API. An optional temporary HTTPS tunnel makes the authenticated app reachable for an evaluator while the computer stays awake. See [deployment](docs/09-deployment.md). This is not a claim of permanently free, always-on hosting for a model and arbitrary-code runner.

## Data and execution boundaries

Keep `.env*`, `.local`, model credentials and database backups private. The application cannot execute source on its host. Approved snapshots run in disposable containers without network, host mounts, credentials or Docker socket access. Keep the runner on a dedicated personal Docker context; do not use office infrastructure. Never deploy the intentionally vulnerable review fixture.
