import subprocess, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.config import settings

context = settings().docker_context
subprocess.run(
    [
        "docker",
        "--context",
        context,
        "build",
        "-t",
        "devsphere-sandbox:1",
        str(root / "sandbox"),
    ],
    check=True,
)
