"""Inspect or explicitly advance a live demonstration checkpoint."""

import argparse, json
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument(
    "action", choices=["start", "status", "approve", "change", "cancel", "retry"]
)
p.add_argument("project", choices=["url", "commerce", "review"])
p.add_argument("--comment", default="")
p.add_argument("--workflow", default="full")
p.add_argument("--approval-id")
args = p.parse_args()
name = {
    "url": "URL Shortener",
    "commerce": "E-commerce Studio",
    "review": "Node Code Review",
}[args.project]
id = json.loads((ROOT / ".local/demo-projects.json").read_text())[name]
auth = json.loads((ROOT / ".local/demo-account.json").read_text())
with httpx.Client(base_url="http://localhost:8010", timeout=30) as c:
    session_path = ROOT / ".local/demo-session.json"
    if session_path.exists():
        c.headers["Authorization"] = "Bearer " + json.loads(session_path.read_text())["access_token"]
    if c.get('/api/auth/me').status_code != 200:
        r = c.post("/api/auth/login", json={k: auth[k] for k in ["email", "password"]})
        r.raise_for_status()
        token = r.json()["access_token"]
        session_path.write_text(json.dumps({"access_token":token}))
        session_path.chmod(0o600)
        c.cookies.clear()
        c.headers["Authorization"] = "Bearer " + token
    base = f"/api/projects/{id}"
    if args.action == "start":
        r = c.post(
            base + "/execute",
            json={"workflow_type": args.workflow, "instructions": args.comment},
        )
        print(r.status_code, r.text)
    elif args.action in {"cancel", "retry"}:
        r = c.post(base + "/" + args.action)
        print(r.status_code, r.text)
    elif args.action in {"approve", "change"}:
        approvals = c.get(base + "/approvals").json()
        a = next(
            (
                a
                for a in approvals
                if a["status"] == "pending" and a["id"] == args.approval_id
            ),
            None,
        )
        if not a:
            raise SystemExit(
                "Pass the exact pending --approval-id after reviewing it with status."
            )
        project = c.get(base).json()
        r = c.post(
            base + f"/approvals/{a['id']}/decision",
            json={
                "decision": "approve" if args.action == "approve" else "regenerate",
                "artifact_hash": a["artifact_hash"],
                "expected_revision": project["revision"],
                "comment": args.comment,
            },
        )
        print(r.status_code, r.text)
    else:
        w = c.get(base + "/workflow").json()
        approvals = c.get(base + "/approvals").json()
        tests = c.get(base + "/tests").json()
        (ROOT / f".local/{args.project}-workflow.json").write_text(
            json.dumps(
                {"workflow": w, "approvals": approvals, "tests": tests}, indent=2
            )
        )
        run = w.get("run")
        print(
            json.dumps(
                {
                    "run": run,
                    "tasks": [
                        {
                            "id": t["id"],
                            "name": t["task_name"],
                            "status": t["task_status"],
                            "error": t["error_message"],
                        }
                        for t in w["tasks"]
                    ],
                    "pending": [a for a in approvals if a["status"] == "pending"],
                    "tests": [
                        {k: v for k, v in t.items() if k != "details"} for t in tests
                    ],
                },
                indent=2,
            )
        )
