"""Trusted recipe driver, baked into the read-only sandbox image."""

import json, os, re, tarfile, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path
import resource

resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as archive:
    archive.extractall("/workspace", filter="data")
recipe = sys.argv[1]
if recipe == "python":
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-q",
        "--junitxml=/tmp/result.xml",
        "-p",
        "no:cacheprovider",
    ]
elif recipe == "node":
    Path("/workspace/node_modules").symlink_to(
        "/deps/node_modules", target_is_directory=True
    )
    tests = sorted(
        str(p)
        for p in Path("tests").rglob("*")
        if p.is_file() and p.suffix in {".js", ".cjs", ".mjs"}
    )
    command = ["node", "--test", "--test-reporter=tap", *tests] if tests else None
elif recipe == "java":
    sources = [str(p) for p in Path(".").rglob("*.java")]
    Path("/workspace/classes").mkdir(exist_ok=True)
    built = subprocess.run(
        ["javac", "-d", "classes", *sources],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if built.returncode:
        print(built.stdout[-20000:])
        sys.exit(built.returncode)
    command = ["java", "-Xmx128m", "-cp", "classes", "TestMain"]
else:
    raise SystemExit("Unsupported trusted recipe")
if not command:
    raise SystemExit("No test files discovered")
with open("/workspace/test-output.txt", "w") as output:
    done = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
log = Path("/workspace/test-output.txt").read_text(errors="replace")[-50000:]
print(log)
counts = {"total": None, "passed": None, "failed": None, "skipped": None}
try:
    if recipe == "python":
        root = ET.parse("/tmp/result.xml").getroot()
        suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
        total = sum(int(s.get("tests", "0")) for s in suites)
        failed = sum(
            int(s.get("failures", "0")) + int(s.get("errors", "0")) for s in suites
        )
        skipped = sum(int(s.get("skipped", "0")) for s in suites)
        counts = {
            "total": total,
            "passed": total - failed - skipped,
            "failed": failed,
            "skipped": skipped,
        }
    elif recipe == "node":
        get = lambda key: int(re.findall(r"^# " + key + r" (\d+)\s*$", log, re.M)[-1])
        counts = {
            "total": get("tests"),
            "passed": get("pass"),
            "failed": get("fail"),
            "skipped": get("skipped"),
        }
    else:
        m = re.search(r"TESTS total=(\d+) passed=(\d+) failed=(\d+)", log)
        if m:
            counts = {
                "total": int(m[1]),
                "passed": int(m[2]),
                "failed": int(m[3]),
                "skipped": 0,
            }
except (OSError, ValueError, IndexError, ET.ParseError):
    pass
print(
    "DEVSPHERE_RESULT="
    + json.dumps({"exit_code": done.returncode, "counts": counts, "recipe": recipe})
)
sys.exit(done.returncode if done.returncode else (0 if counts["total"] else 5))
