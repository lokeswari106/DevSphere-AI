"""One-command local setup/start. Requires Python 3.12 and personal Docker + Compose.

The API never receives a Docker socket. This launcher starts the trusted host-side
test worker; generated code still runs only in constrained disposable containers.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import venv

ROOT = Path(__file__).resolve().parent


def read_config(path):
    result = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def prepare_config(path, context, *, port=None, database_port=None, model=None, ollama_url=None):
    cfg = read_config(path)
    cfg.setdefault("POSTGRES_PASSWORD", secrets.token_urlsafe(32))
    cfg.setdefault("JWT_SECRET", secrets.token_urlsafe(48))
    cfg.setdefault("APP_PORT", "8010")
    cfg.setdefault("DATABASE_PORT", "55435")
    cfg.setdefault("PROVIDER", "ollama")
    cfg.setdefault("OLLAMA_MODEL", "qwen3:8b")
    cfg.setdefault("OLLAMA_BASE_URL", "http://ollama:11434")
    cfg["DOCKER_CONTEXT"] = context
    for key, value in [("APP_PORT", port), ("DATABASE_PORT", database_port), ("OLLAMA_MODEL", model), ("OLLAMA_BASE_URL", ollama_url)]:
        if value is not None:
            cfg[key] = str(value)
    cfg["APP_ORIGIN"] = "http://localhost:" + cfg["APP_PORT"]
    cfg["SECURE_COOKIE"] = "false"
    cfg["REGISTRATION_ENABLED"] = "true"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{key}={value}\n" for key, value in cfg.items()))
    path.chmod(0o600)
    return cfg


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def compose_command(context, config, project):
    return ["docker", "--context", context, "compose", "--project-name", project, "--env-file", str(config), "--file", str(ROOT / "compose.yaml")]


def ensure_environment():
    directory = ROOT / "backend/.venv"
    python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creating an isolated Python environment…", flush=True)
        venv.EnvBuilder(with_pip=True).create(directory)
    fingerprint = hashlib.sha256((ROOT / "backend/requirements.txt").read_bytes()).hexdigest()
    marker = directory / ".devsphere-requirements"
    if not marker.exists() or marker.read_text() != fingerprint:
        print("Installing the trusted runner dependencies (first start or dependency update)…", flush=True)
        run([str(python), "-m", "pip", "install", "-r", str(ROOT / "backend/requirements.txt")])
        marker.write_text(fingerprint)
    return python


def wait_for_app(port, seconds=150):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/health/ready", timeout=3) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError("The app did not become ready. Run the logs command to see the startup error.")


def check_port(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", int(port)))
        except OSError:
            raise RuntimeError(f"Port {port} is already in use. Stop the existing app or choose --port and --database-port explicitly.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=["start", "status", "logs", "stop"], default="start")
    parser.add_argument("--context", help="Personal Docker context; saved after the first start")
    parser.add_argument("--port", type=int)
    parser.add_argument("--database-port", type=int)
    parser.add_argument("--model", help="Local model name, default qwen3:8b")
    parser.add_argument("--ollama-url", help="Optional existing Ollama URL reachable from the app container")
    parser.add_argument("--config", default=".env.localhost")
    parser.add_argument("--project", default="devsphere-local")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use Python 3.12: python3.12 devsphere.py (macOS/Linux) or py -3.12 devsphere.py (Windows).")
    if not shutil.which("docker"):
        raise RuntimeError("Install and start Docker Desktop, or personal Docker Engine with Compose, then retry.")
    config = (ROOT / args.config).resolve()
    existing = read_config(config)
    context = args.context or existing.get("DOCKER_CONTEXT") or run(["docker", "context", "show"], capture_output=True, text=True).stdout.strip()
    docker = ["docker", "--context", context]
    run(docker + ["info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    endpoint = json.loads(run(docker + ["context", "inspect", context], capture_output=True, text=True).stdout)[0]["Endpoints"]["docker"]["Host"]
    if not endpoint.startswith(("unix://", "npipe://")):
        raise RuntimeError("Local setup requires a personal local Docker daemon, not a remote Docker endpoint.")
    run(docker + ["compose", "version"], stdout=subprocess.DEVNULL)
    compose = compose_command(context, config, args.project)
    control = ROOT / ".local" / ("launcher-" + hashlib.sha256(str(config).encode()).hexdigest()[:12] + ".stop")
    if args.command != "start":
        if not config.exists():
            raise RuntimeError("No local configuration yet. Run the start command first.")
        if existing.get("OLLAMA_BASE_URL") == "http://ollama:11434":
            compose += ["--profile", "local-model"]
        if args.command == "status":
            run(compose + ["ps"])
        elif args.command == "logs":
            run(compose + ["logs", "--tail", "80", "app"])
        else:
            control.parent.mkdir(exist_ok=True)
            control.touch()
            print("Requested graceful worker shutdown. Keeping database/model volumes.", flush=True)
            # The launcher's finally block brings down its own stack after the worker exits.
            for _ in range(60):
                if not run(compose + ["ps", "--status", "running", "--quiet"], capture_output=True, text=True).stdout.strip():
                    return
                time.sleep(2)
            run(compose + ["down"])
        return
    # Never change a saved port while an existing stack is still running.
    if config.exists() and run(compose + ["ps", "--status", "running", "--quiet"], capture_output=True, text=True).stdout.strip():
        raise RuntimeError("This local stack is already running. Use its open terminal, or stop it before restarting.")
    port = args.port or int(existing.get("APP_PORT", 8010))
    database_port = args.database_port or int(existing.get("DATABASE_PORT", 55435))
    for value in [port, database_port]:
        if not 1024 <= value <= 65535:
            raise RuntimeError("Choose local ports from 1024 through 65535.")
        check_port(value)
    if port == database_port:
        raise RuntimeError("The app and database must use different ports.")
    cfg = prepare_config(config, context, port=port, database_port=database_port, model=args.model, ollama_url=args.ollama_url)
    local_model = cfg["PROVIDER"] == "ollama" and cfg["OLLAMA_BASE_URL"] == "http://ollama:11434"
    if cfg["PROVIDER"] == "openai" and not (cfg.get("OPENAI_API_KEY") and cfg.get("OPENAI_MODEL")):
        raise RuntimeError("Set OPENAI_API_KEY and OPENAI_MODEL in the private configuration, or use the default local Ollama model.")
    if local_model:
        compose += ["--profile", "local-model"]
    print(f"Using personal Docker context: {context}", flush=True)
    print("First startup downloads dependencies, images and the AI model. Later starts reuse them.", flush=True)
    python = ensure_environment()
    control.parent.mkdir(exist_ok=True)
    control.unlink(missing_ok=True)
    child = None
    started = False
    try:
        run(docker + ["build", "-t", "devsphere-sandbox:1", str(ROOT / "sandbox")])
        started = True
        run(compose + ["up", "--build", "-d"])
        if local_model:
            print("Downloading/checking the real local AI model…", flush=True)
            for attempt in range(30):
                check = subprocess.run(compose + ["exec", "-T", "ollama", "ollama", "list"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if check.returncode == 0:
                    break
                time.sleep(2)
            else:
                raise RuntimeError("The local Ollama service did not start. Check Docker's memory allocation and logs.")
            run(compose + ["exec", "-T", "ollama", "ollama", "pull", cfg["OLLAMA_MODEL"]])
        wait_for_app(port)
        env = {**os.environ, "DEVSPHERE_CONFIG_FILE": str(config), "DEVSPHERE_STOP_FILE": str(control)}
        # Separate process, separate trust boundary: the API has no Docker access.
        child = subprocess.Popen([str(python), str(ROOT / "scripts/start_compose_runner.py")], cwd=ROOT, env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
        print(f"\nDevSphere AI is ready: http://localhost:{port}\nCreate your own account. Keep this terminal open. Ctrl+C stops this stack without deleting projects.\n", flush=True)
        while child.poll() is None:
            time.sleep(1)
        if control.exists():
            return
        raise RuntimeError("The test worker stopped. Inspect its message above and restart the launcher.")
    except KeyboardInterrupt:
        print("\nStopping DevSphere; waiting for any isolated test to finish…", flush=True)
    finally:
        if child and child.poll() is None:
            if os.name == "nt":
                child.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                child.terminate()
            try:
                child.wait(timeout=110)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        if started:
            # No --volumes: users, projects and model cache survive a normal stop.
            run(compose + ["down"])


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            print("\nA setup command failed. Check its error above; ensure Docker is running and internet is available for first-time downloads.", file=sys.stderr)
        else:
            print("\n" + str(error), file=sys.stderr)
        sys.exit(1)
