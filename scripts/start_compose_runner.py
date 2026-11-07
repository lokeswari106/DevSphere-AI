"""Host-side trusted worker; the web application has no Docker access."""

import os, sys, runpy
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
cfg = dotenv_values(Path(os.environ.get("DEVSPHERE_CONFIG_FILE", root / ".env.compose")))
if not cfg.get("POSTGRES_PASSWORD"):
    raise SystemExit("Run scripts/configure_compose.py first")
os.environ.update(
    {
        "DATABASE_URL": f"postgresql+psycopg://devsphere:{cfg['POSTGRES_PASSWORD']}@127.0.0.1:{cfg.get('DATABASE_PORT', '55434')}/devsphere",
        "JWT_SECRET": cfg["JWT_SECRET"],
        "DOCKER_CONTEXT": cfg.get("DOCKER_CONTEXT", "default"),
    }
)
runpy.run_path(str(root / "scripts/run_sandbox_worker.py"), run_name="__main__")
