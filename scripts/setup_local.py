"""Initialize only DevSphere's own local database and ignored credentials."""

from pathlib import Path
import json, os, secrets, subprocess, shutil

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
LOCAL.mkdir(exist_ok=True)
EXE = ".exe" if os.name == "nt" else ""
PG = Path(os.environ.get("PG_BIN", "/opt/homebrew/opt/postgresql@17/bin"))
if not (PG / ("initdb" + EXE)).exists():
    found = shutil.which("initdb")
    if not found:
        raise SystemExit(
            "Install PostgreSQL 17 and set PG_BIN to its bin directory, or use Docker Compose."
        )
    PG = Path(found).parent
admin_file = LOCAL / "postgres-admin.json"
if not admin_file.exists():
    admin_file.write_text(
        json.dumps(
            {
                "password": secrets.token_urlsafe(32),
                "app_password": secrets.token_urlsafe(32),
            }
        )
    )
    admin_file.chmod(0o600)
auth = json.loads(admin_file.read_text())
data = LOCAL / "postgres"
pwfile = LOCAL / "initdb-password"
if not (data / "PG_VERSION").exists():
    pwfile.write_text(auth["password"])
    pwfile.chmod(0o600)
    try:
        subprocess.run(
            [
                str(PG / ("initdb" + EXE)),
                "-D",
                str(data),
                "-U",
                "devsphere_admin",
                "--auth=scram-sha-256",
                f"--pwfile={pwfile}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    finally:
        pwfile.unlink(missing_ok=True)
    with (data / "postgresql.conf").open("a") as f:
        f.write(
            "\nport=55433\nlisten_addresses='127.0.0.1'\nmax_connections=30\nshared_buffers='64MB'\n"
        )
        if os.name != "nt":
            f.write(f"unix_socket_directories='{LOCAL}'\n")
if subprocess.run(
    [str(PG / ("pg_ctl" + EXE)), "-D", str(data), "status"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
).returncode:
    subprocess.run(
        [
            str(PG / ("pg_ctl" + EXE)),
            "-D",
            str(data),
            "-l",
            str(LOCAL / "postgres.log"),
            "start",
        ],
        check=True,
    )
import psycopg
from psycopg import sql

with psycopg.connect(
    host="127.0.0.1",
    port=55433,
    user="devsphere_admin",
    password=auth["password"],
    dbname="postgres",
    autocommit=True,
) as conn:
    if not conn.execute(
        "SELECT 1 FROM pg_roles WHERE rolname='devsphere_app'"
    ).fetchone():
        conn.execute(
            sql.SQL("CREATE ROLE devsphere_app LOGIN PASSWORD {}").format(
                sql.Literal(auth["app_password"])
            )
        )
    for name in ["devsphere", "devsphere_test"]:
        if not conn.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", (name,)
        ).fetchone():
            conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER devsphere_app").format(
                    sql.Identifier(name)
                )
            )
if not (ROOT / ".env").exists():
    (ROOT / ".env").write_text(
        f"DATABASE_URL=postgresql+psycopg://devsphere_app:{auth['app_password']}@127.0.0.1:55433/devsphere\nJWT_SECRET={secrets.token_urlsafe(48)}\nAPP_ORIGIN=http://localhost:8010\nPROVIDER=ollama\nOLLAMA_MODEL=qwen3:8b\nDOCKER_CONTEXT=colima-devsphere\n"
    )
    (ROOT / ".env").chmod(0o600)
print(
    "DevSphere PostgreSQL ready on 127.0.0.1:55433. Credentials stay in ignored local files."
)
