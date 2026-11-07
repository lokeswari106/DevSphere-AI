"""Run the trusted API and runner. Ctrl+C stops both; project data is retained."""

import os, sys, subprocess, signal, time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if not (root / "frontend/dist/index.html").exists():
    raise SystemExit(
        "Build the frontend first: npm ci --prefix frontend && npm run build --prefix frontend"
    )
subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=root / "backend",
    check=True,
)
children = []
try:
    children.append(
        subprocess.Popen(
            [sys.executable, str(root / "scripts/run_sandbox_worker.py")], cwd=root
        )
    )
    children.append(
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                os.environ.get("APP_PORT", "8010"),
                "--no-proxy-headers",
            ],
            cwd=root / "backend",
        )
    )
    print(
        "Open http://localhost:"
        + os.environ.get("APP_PORT", "8010")
        + " ; Ctrl+C to stop.",
        flush=True,
    )
    while all(p.poll() is None for p in children):
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    for p in children:
        if p.poll() is None:
            p.terminate()
    for p in children:
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
