"""Create personal Compose secrets. Never replaces an existing configuration."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = root / ".env.compose"
if p.exists():
    raise SystemExit(
        ".env.compose already exists; edit it instead of replacing credentials."
    )
p.write_text(
    f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\nJWT_SECRET={secrets.token_urlsafe(48)}\nAPP_PORT=8010\nDATABASE_PORT=55434\nAPP_ORIGIN=http://localhost:8010\nPROVIDER=ollama\nOLLAMA_MODEL=qwen3:8b\nOLLAMA_BASE_URL=http://ollama:11434\nDOCKER_CONTEXT=default\n"
)
p.chmod(0o600)
print("Created .env.compose. Use --env-file .env.compose with every Compose command.")
