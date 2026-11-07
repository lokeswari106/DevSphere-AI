"""Export the owned live demonstrations, never account credentials or invented results."""

import json
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
account = json.loads((ROOT / ".local/demo-account.json").read_text())
projects = json.loads((ROOT / ".local/demo-projects.json").read_text())
out = ROOT / "samples/live"
out.mkdir(parents=True, exist_ok=True)
summary = {"recorded_at": datetime.now(timezone.utc).isoformat(), "provider": "real Ollama", "projects": []}
with httpx.Client(base_url="http://localhost:8010", timeout=60) as client:
    session_path = ROOT / ".local/demo-session.json"
    if session_path.exists():
        client.headers["Authorization"] = "Bearer " + json.loads(session_path.read_text())["access_token"]
    if client.get("/api/auth/me").status_code != 200:
        response = client.post("/api/auth/login", json={k: account[k] for k in ("email", "password")})
        response.raise_for_status()
        token = response.json()["access_token"]
        session_path.write_text(json.dumps({"access_token": token}))
        session_path.chmod(0o600)
        client.cookies.clear()
        client.headers["Authorization"] = "Bearer " + token
    for name, pid in projects.items():
        base = "/api/projects/" + pid
        folder = out / name.lower().replace(" ", "-")
        folder.mkdir(exist_ok=True)
        data = {}
        for endpoint in ("workflow", "agent-tasks", "approvals", "files", "documents", "tests", "reviews", "versions", "events"):
            response = client.get(base + "/" + endpoint)
            response.raise_for_status()
            data[endpoint] = response.json()
        (folder / "evidence.json").write_text(json.dumps(data, indent=2))
        for f in data["files"]:
            # The API validates paths, but retain a second export boundary.
            rel = Path(f["file_path"])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("Unsafe export path")
            target = folder / "approved-source" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f["file_content"])
        for d in data["documents"]:
            if d["document_type"] == "documentation" and not d.get("stale"):
                for key, content in d["document_content"].items():
                    if key.endswith("_markdown"):
                        (folder / (key.removesuffix("_markdown") + ".md")).write_text(content)
                response = client.get(base + "/documents/" + d["id"] + "/download", params={"format":"pdf","section":"final_report"})
                response.raise_for_status()
                (folder / "final_report.pdf").write_bytes(response.content)
                break
        run = data["workflow"].get("run") or {}
        summary["projects"].append({"name": name, "run_id": run.get("id"), "status": run.get("status"), "stage": run.get("stage"), "test_runs": [{k: t[k] for k in ("id", "source_hash", "test_status", "total_tests", "passed_tests", "failed_tests")} for t in data["tests"]]})
(out / "status.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
