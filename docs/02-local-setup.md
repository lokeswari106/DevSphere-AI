# Run DevSphere AI on another computer

This project is separate from AgentSphere. Copy the DevSphereAI source archive or repository into a new folder. Do not copy `.env`, `.env.compose`, `.local`, virtual environments or database files from someone else's machine. Create your own account; registration has no invitation token.

## Simplest route: one launcher command

For a fresh Windows, macOS or Linux machine, follow [RUN_LOCALLY.md](../RUN_LOCALLY.md). Install Python 3.12 and Docker, then run `python3.12 devsphere.py` (Windows: `py -3.12 devsphere.py`). It prepares and starts the full local stack, including the separate sandbox worker. The routes below remain available for advanced/native setup.

## Choose a route

- **Native local route:** Python 3.12, Node.js 22.12 or newer, PostgreSQL 17, Ollama, and Docker. Native Ollama uses the computer's available acceleration. This is the route used for the recorded live demo on macOS.
- **Docker route:** Docker Desktop/Engine with Compose, Python 3.12 for the separate runner, and internet for initial image/model downloads. The web application and PostgreSQL run in containers. The optional Ollama service runs a local model in a container.

Allow roughly 12–16 GB available system memory for an 8B local model plus the application, and 15 GB free disk space for images/model/dependencies. These are planning estimates, not measured minimum requirements. A smaller compatible model may work but must be evaluated. Using OpenAI removes the local-model memory requirement and may incur API charges. No paid provider is required for the local demonstration.

## Route A: native installation

### 1. Open the project directory

On macOS/Linux use Terminal. On Windows use PowerShell, or WSL2 Ubuntu with all native steps inside WSL. Paths below are relative to the extracted project root.

### 2. Create a Python environment

macOS/Linux:

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv backend/.venv
backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

For subsequent commands, replace `backend/.venv/bin/python` with `backend\.venv\Scripts\python.exe` on Windows. Use a Python 3.12 interpreter, not the operating system's protected Python environment.

### 3. Initialize PostgreSQL

Install PostgreSQL 17 from its official installer or package manager. This helper creates a project-owned database cluster on **127.0.0.1:55433**. It does not alter a pre-existing PostgreSQL installation's databases. Do not run it as root.

macOS example:

```sh
brew install postgresql@17
PG_BIN=/opt/homebrew/opt/postgresql@17/bin backend/.venv/bin/python scripts/setup_local.py
```

Linux example (adjust the installed binary path):

```sh
PG_BIN=/usr/lib/postgresql/17/bin backend/.venv/bin/python scripts/setup_local.py
```

Windows PowerShell example:

```powershell
$env:PG_BIN="C:\Program Files\PostgreSQL\17\bin"
backend\.venv\Scripts\python.exe scripts/setup_local.py
```

The helper creates the `devsphere` and separate `devsphere_test` databases, random database credentials, and `.env`. Rerunning starts the existing project cluster without replacing credentials. The application stores records in PostgreSQL, not SQLite.

If you already have a personal PostgreSQL service, create an owned database and set `DATABASE_URL` in a copied `.env.example`. Create a separate `devsphere_test` database for automated tests. Never point test configuration at a database containing valuable data.

### 4. Prepare the real local model

Install Ollama from [its official site](https://ollama.com/download), start it, then run:

```sh
ollama pull qwen3:8b
ollama list
```

The model download requires internet. Subsequent native Ollama inference can run locally. `.env` must contain `PROVIDER=ollama`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`, and `OLLAMA_MODEL=qwen3:8b`. Keep Ollama bound to loopback. There is no mock fallback in the live application.

### 5. Prepare the isolated runner

macOS with Colima (dedicated VM; does not change the active Docker context):

```sh
brew install colima docker
colima start devsphere --activate=false --cpu 2 --memory 3 --disk 16 --mount none
```

Set `DOCKER_CONTEXT=colima-devsphere` in `.env`. On Docker Desktop use the intended personal context reported by `docker context ls`, such as `desktop-linux`. On Linux use a dedicated/rootless personal Docker daemon and its context. Do not reuse an office daemon.

```sh
backend/.venv/bin/python scripts/build_sandbox.py
```

Only the separate trusted worker has Docker access. The generated test container has no Docker socket, host mounts, network, API keys or database credentials. Its image includes fixed Python, Node and Java test tools. Adding a new dependency requires a reviewed rebuild of `sandbox/Dockerfile`; generated requirements are never installed automatically.

### 6. Build the JavaScript frontend

```sh
npm ci --prefix frontend
npm run build --prefix frontend
```

### 7. Start the application and worker

```sh
backend/.venv/bin/python scripts/start_local.py
```

This applies Alembic migrations, starts FastAPI and starts the separate runner. Keep this terminal open. Visit **http://localhost:8010**, choose **Create an account**, enter a name, email and password of at least 12 characters, and sign in. No invitation token is required.

API documentation: **http://localhost:8010/docs**. Health checks: `/health/live` and `/health/ready`. Swagger loads its standard UI assets from jsDelivr; the main dashboard uses bundled local assets. Raw `/openapi.json` remains available without the Swagger CDN.

### 8. Stop and restart

Press Ctrl+C in the application terminal. Records remain in PostgreSQL. Re-run step 7 to resume. If PostgreSQL is stopped, rerun `scripts/setup_local.py`. Never delete `.local/postgres` as a routine restart operation.

## Route B: Docker Compose installation

### 1. Create local configuration

```sh
python3 scripts/configure_compose.py
```

Windows: `py -3.12 scripts/configure_compose.py`. The script creates `.env.compose` with random secrets. Edit `DOCKER_CONTEXT` to your personal daemon context. Set `APP_PORT`/`APP_ORIGIN` together if 8010 is occupied. Keep this file private.

### 2. Start PostgreSQL, web application and local Ollama

Replace `<personal-context>` in each command with the personal Docker context selected in step 1. The CLI context is explicit; the Compose env file does not select the daemon for you.

```sh
docker --context <personal-context> compose --env-file .env.compose --profile local-model up --build -d
docker --context <personal-context> compose --env-file .env.compose exec ollama ollama pull qwen3:8b
docker --context <personal-context> compose --env-file .env.compose ps
```

Allocate sufficient Docker VM RAM for the local model; the small 3 GB sandbox VM alone is not sized for an 8B model. CPU-only inference can be slower. On macOS, the native route can use native Ollama acceleration. To use OpenAI instead, set `PROVIDER=openai`, `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env.compose`, omit `--profile local-model`, and restart the app. Do not commit these values.

### 3. Build and start the separate host-side runner

Create the Python environment and install backend dependencies as in Route A. Build the sandbox in the same personal Docker context. Replace `<personal-context>` with the context selected in `.env.compose`:

```sh
docker --context <personal-context> build -t devsphere-sandbox:1 sandbox
backend/.venv/bin/python scripts/start_compose_runner.py
```

The worker connects to PostgreSQL through loopback port 55434 and controls isolated test containers. It is deliberately not a service with a Docker socket mounted into the web application.

### 4. Open and operate

Visit **http://localhost:8010**. Create your own account. In Settings, confirm the test runner is **Online** and its image is **Ready**. Inspect failures with:

```sh
docker --context <personal-context> compose --env-file .env.compose logs --tail=100 app
```

Stop with `docker --context <personal-context> compose --env-file .env.compose down`. Named volumes retain data. Do **not** use `down -v` unless intentionally deleting the project database and model cache.

## Optional frontend development

With the backend on 8010:

```sh
npm run dev --prefix frontend
```

Visit http://localhost:5174. Vite proxies `/api` to FastAPI, keeping browser requests same-origin. Compile the frontend again before using the single-server production build on 8010.

## Troubleshooting

| Symptom | Check and resolution |
| --- | --- |
| Cannot open localhost | Keep the application terminal running; confirm port 8010 is free; request `/health/live`. |
| Readiness fails | Check database credentials, PostgreSQL process and `alembic upgrade head`. |
| Provider unavailable | Confirm `ollama list`, model name and provider URL; no fabricated response is substituted. |
| Workflow pauses | An approval is required. Inspect the proposal before selecting Approve and continue. |
| Invalid model JSON | Read agent errors; narrow the requirement or request regeneration. Three attempts are recorded. |
| Test runner offline | Start exactly one runner process; confirm Docker context and built sandbox image. |
| Tests fail on imports | The sandbox has a fixed dependency set. Review generated dependencies or rebuild the trusted image. |
| Stale proposal conflict | Refresh, review the newest revision, and approve its new hash. |
| Invalid diagram | The UI shows source when parsing fails. Edit the proposal or request corrected Mermaid. |
| Registration rejected | Local default allows registration. Temporary public demos may disable it. |
| Forgotten account password | This version has no self-service reset. Create a separate local account or implement a reviewed reset workflow; do not expose the database publicly. |

## Backup

Use `pg_dump` against your own database and store the backup privately. Stop the application while restoring into a **new** database, apply compatible migrations, update `DATABASE_URL`, and validate ownership and sample projects. The project ZIP exports approved source/documents, not user accounts or the full database. Keep secrets outside the source archive.
