"""Called only by the separate trusted runner process. No user code executes here."""

import io, json, subprocess, tarfile, time, uuid, re
from app.config import settings
from app.services.artifacts import validate_files

IMAGE = "devsphere-sandbox:1"


def docker(*args, timeout=30, input=None):
    return subprocess.run(
        ["docker", "--context", settings().docker_context, *args],
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def available():
    if not settings().sandbox_enabled:
        return False
    try:
        return docker("image", "inspect", IMAGE, timeout=5).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def execute_snapshot(files, recipe, time_limit=None):
    validate_files(files)
    if recipe not in {"python", "node", "java"}:
        raise ValueError("Unknown sandbox recipe")
    if not available():
        return {
            "status": "unavailable",
            "log": "Sandbox image is unavailable in the configured dedicated Docker context.",
            "total": None,
            "passed": None,
            "failed": None,
        }
    name = "devsphere-" + uuid.uuid4().hex
    flags = [
        "create",
        "-i",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/workspace:rw,nosuid,nodev,size=64m,mode=1777",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777",
        "--memory",
        "512m",
        "--memory-swap",
        "512m",
        "--cpus",
        "1",
        "--pids-limit",
        "64",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "65532:65532",
        "--ulimit",
        "nofile=128:128",
        "--log-driver",
        "local",
        "--log-opt",
        "max-size=1m",
        "--log-opt",
        "max-file=1",
        "--log-opt",
        "compress=false",
        IMAGE,
        recipe,
    ]
    started = time.monotonic()
    created = False
    try:
        result = docker(*flags)
        if result.returncode:
            raise RuntimeError(result.stderr.decode()[:500])
        created = True
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as tar:
            for f in files:
                data = f["content"].encode()
                info = tarfile.TarInfo(f["path"])
                info.size = len(data)
                info.mode = 0o444
                info.uid = 65532
                info.gid = 65532
                tar.addfile(info, io.BytesIO(data))
        try:
            wait = docker(
                "start",
                "--attach",
                "--interactive",
                name,
                input=archive.getvalue(),
                timeout=time_limit or settings().sandbox_timeout,
            )
            exit_code = json.loads(docker("inspect", name).stdout)[0]["State"][
                "ExitCode"
            ]
        except subprocess.TimeoutExpired:
            docker("kill", name)
            return {
                "status": "timed_out",
                "log": docker("logs", name).stdout.decode(errors="replace")[-50000:]
                + "\nSupervisor terminated this container at the time limit.",
                "total": None,
                "passed": None,
                "failed": None,
                "duration": time.monotonic() - started,
            }
        inspected = json.loads(docker("inspect", name).stdout)[0]["State"]
        output = docker("logs", name)
        log = (output.stdout + output.stderr).decode(errors="replace")[-60000:]
        matches = re.findall(r"^DEVSPHERE_RESULT=(.+)$", log, re.M)
        counts = {}
        if matches:
            try:
                counts = json.loads(matches[-1]).get("counts", {})
            except ValueError:
                pass
        status = (
            "passed"
            if exit_code == 0 and counts.get("total", 0) and counts.get("failed") == 0
            else "failed"
        )
        if inspected.get("OOMKilled"):
            status = "resource_limit"
        return {
            "status": status,
            "log": log
            + str(inspected.get("Error", ""))
            + wait.stderr.decode(errors="replace")[-2000:],
            "total": counts.get("total"),
            "passed": counts.get("passed"),
            "failed": counts.get("failed"),
            "skipped": counts.get("skipped"),
            "exit_code": exit_code,
            "duration": time.monotonic() - started,
            "oom_killed": inspected.get("OOMKilled", False),
            "image": IMAGE,
            "network": "none",
            "counts_basis": "test framework output from actual execution",
        }
    finally:
        if created:
            docker("rm", "-f", name)
