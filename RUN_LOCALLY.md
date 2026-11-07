# Run the complete project on localhost

Use these steps on your own Windows, macOS or Linux computer. You do not need a GitHub account or a paid AI key to run the default local model.

## 1. Install the required software

| Installation | Required? | Purpose |
| --- | --- | --- |
| **Python 3.12** from [python.org](https://www.python.org/downloads/) | Yes | Runs the launcher and the separate trusted test worker. |
| **Docker Desktop**, opened and running | Yes, or Docker Engine + Compose on Linux | Runs the application, PostgreSQL, local model and isolated test containers. See [Docker installation](https://docs.docker.com/compose/install/). Use Linux containers on Windows. |
| **Git** from [git-scm.com](https://git-scm.com/downloads) | Optional | Downloads the repository with `git clone`. Download ZIP works without Git. |
| A current web browser | Yes | Opens the interface at `http://localhost:8010`. |

You do **not** need to install Node.js, npm, PostgreSQL or Ollama separately for this launcher. Docker builds and starts them. A paid AI API key is not required for the default local model.

On Windows, install Python 3.12 with the Python launcher (`py`). If Docker Desktop requests WSL 2 setup, virtualization support or a restart, finish those installation steps before starting this project. On macOS, select the Docker Desktop download for your processor (Apple silicon or Intel). On Linux, install Python 3.12 with its `venv` support, Docker Engine and the Compose plugin, then ensure your account can access your personal Docker daemon.

Check the installations in a new terminal:

**Windows PowerShell:**

```powershell
py -3.12 --version
docker --version
docker compose version
docker info
```

**macOS/Linux:**

```sh
python3.12 --version
docker --version
docker compose version
docker info
```

Python must report `3.12.x`; `docker info` must connect to the running local Docker engine. If either check fails, finish installing or starting that prerequisite before continuing.

An 8B local model needs a capable machine. Plan for roughly **16 GB system RAM**, enough memory allocated to Docker, and **15–20 GB free disk**. These are estimates, not a guaranteed minimum. First-time image, package and model downloads require internet. CPU inference can take several minutes. Docker's local Ollama mode is documented [here](https://docs.ollama.com/docker).

## 2. Download the project and open its folder

Choose either method:

**With Git:**

```sh
git clone https://github.com/lokeswari106/DevSphere-AI.git
cd DevSphere-AI
```

**Without Git:** open [the GitHub repository](https://github.com/lokeswari106/DevSphere-AI), choose **Code → Download ZIP**, then extract it. Open Terminal or PowerShell in the extracted **DevSphere-AI-main** folder. If using the separately packaged `DevSphere-AI-Source.zip`, open its **DevSphereAI** folder instead.

In either case, the current folder must contain `devsphere.py`, `compose.yaml`, `frontend` and `backend`. On Windows, use **Open in Terminal** from the extracted folder; on macOS/Linux, use `cd` with the actual extracted path.

## 3. Run one command

**Windows PowerShell:**

```powershell
py -3.12 devsphere.py
```

**macOS/Linux:**

```sh
python3.12 devsphere.py
```

The launcher creates private random credentials, prepares the Python test worker, builds the React/FastAPI application and sandbox images, starts PostgreSQL and Ollama, downloads `qwen3:8b`, applies database migrations and starts the separate test worker. The first start takes longer; later starts reuse downloaded packages, models and images. There are no manual Node.js, PostgreSQL or Ollama installation steps for this route.

The launcher uses your selected **personal local Docker context** and remembers it in `.env.localhost`. If you have multiple contexts, use `docker context ls` and explicitly select your personal one:

```sh
python3.12 devsphere.py --context desktop-linux
```

Replace `desktop-linux` with the actual personal context name. On Windows, replace `python3.12` with `py -3.12`. Do not point this project at an office or remote Docker daemon.

## 4. Open the app

Open **http://localhost:8010**. Create an account with your own name, email and password. No invitation token is required.

- **New Project:** describe the application, approve each generated proposal and run tests when prompted.
- **Code review:** paste code or upload source files, then select **Save & review code**. Findings include explanations and replacement suggestions that you can copy or download.
- **Testing:** inspect actual sandbox results and logs. A failed test is shown as failed; it is never replaced with a simulated success.
- **Settings:** confirm the runner is online and its sandbox image is ready.
- API documentation: **http://localhost:8010/docs**.

Keep the launcher terminal open while you use the app.

## 5. Stop and restart

Press **Ctrl+C** in the launcher terminal. It stops its worker and containers while retaining projects, accounts and the model cache. If tests are running, allow up to about two minutes for a controlled stop.

To restart, run the **same command from step 3**. Do not delete `.env.localhost`: its credentials are needed to reopen the existing database volume.

From another terminal you can use:

```sh
python3.12 devsphere.py status
python3.12 devsphere.py logs
python3.12 devsphere.py stop
```

Do not use `docker compose down -v` for an ordinary stop; that can remove stored data.

## Common fixes

| Problem | What to do |
| --- | --- |
| Python command not found | Install Python 3.12. On Windows use `py -3.12`; on macOS/Linux use `python3.12`. |
| Python cannot create a virtual environment | Install the `venv`/`ensurepip` support for Python 3.12 using your operating system's Python installation instructions, then rerun the launcher. |
| Docker unavailable | Open Docker Desktop and wait until its engine is ready; on Linux ensure your account can use your personal Docker daemon. |
| Port already in use | Stop the older instance, or start with `--port 8020 --database-port 55440`, then open `http://localhost:8020`. The selected ports are remembered. |
| Model download fails | Check internet access, free disk and Docker memory. Run the launcher again; saved configuration is retained. |
| Model is slow | Increase Docker memory or try `--model qwen3:4b`. A smaller model may produce weaker code and still requires review. |
| A workflow is waiting | Inspect the pending proposal and choose Approve, Reject or Request changes. |
| Tests fail | Open the execution log. New dependencies require a reviewed sandbox rebuild; uploaded requirements are never installed automatically. |
| Existing native installation | It can continue using `scripts/start_local.py`. The one-command route uses its own Compose database and `.env.localhost`; it does not migrate the native database automatically. |

## Existing local Ollama (optional)

On macOS, native Ollama can use acceleration unavailable to a CPU-only Docker container. If you already run a model and have made its API reachable from your personal Docker VM, use:

```sh
python3.12 devsphere.py --ollama-url http://host.docker.internal:11434
```

The hostname must be reachable from the container; Colima can use `host.lima.internal`. Install/pull your selected model in that existing Ollama service first. The default command needs no external Ollama service.

## Copying to another computer

Copy the source ZIP, not `.env*`, `.local`, virtual environments or someone else's database. Repeat steps 1–4 to create a clean local installation. Project exports contain generated source and documents; they do not migrate platform accounts. See [the full setup guide](docs/02-local-setup.md) for backup and advanced native installation.

## Updating a Git clone later

Stop the launcher with **Ctrl+C**, then run these commands from the project folder:

```sh
git pull --ff-only
python3.12 devsphere.py
```

On Windows use `py -3.12 devsphere.py` for the second command. If Git reports local changes or a conflict, keep those changes and resolve the message before updating; do not delete your configuration or database volumes. The launcher rebuilds updated images and installs changed trusted runner dependencies on the next start.

The launcher is designed for Windows, macOS and Linux. [The actual verification record](docs/portable-verification.json) confirms startup, a real model review, an isolated test and persistence after stop/restart on macOS with Linux containers. That check used existing native Ollama; the bundled model-download path and a fresh Windows installation were not exercised.
