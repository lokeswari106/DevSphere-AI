"""Create a local demonstration account and projects; do not auto-approve agent work."""

from pathlib import Path
import json, secrets, httpx

ROOT = Path(__file__).resolve().parents[1]
dest = ROOT / ".local/demo-account.json"
if dest.exists():
    auth = json.loads(dest.read_text())
else:
    auth = {
        "email": "student@example.com",
        "password": secrets.token_urlsafe(20),
        "name": "Student",
    }
    dest.write_text(json.dumps(auth, indent=2))
    dest.chmod(0o600)
with httpx.Client(base_url="http://localhost:8010") as c:
    r = c.post("/api/auth/login", json={k: auth[k] for k in ["email", "password"]})
    if r.status_code == 401:
        r = c.post("/api/auth/register", json=auth)
    r.raise_for_status()
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    projects = c.get("/api/projects").json()
    saved = {}
    descriptions = {
        "URL Shortener": "Build a compact URL shortener API in FastAPI with SQLite persistence. POST /links accepts a validated public http or https URL and returns a unique short code. GET /r/{code} redirects and increments click count; GET /links/{code} returns stats. Reject javascript/file URLs and missing codes with appropriate errors. Include collision handling and meaningful tests. No login is required for this demonstration.",
        "E-commerce Studio": "Build a small e-commerce demonstration with FastAPI and React JavaScript. Include email/password registration and login with securely hashed passwords, product listing, a shopping cart, order creation and order history with per-user ownership. Use SQLite for a self-contained generated demo. Provide a clearly labelled test-mode payment adapter that never processes real money. Keep the app compact but runnable. Explain remaining production work.",
        "Node Code Review": "Analyze my uploaded Node.js application and identify bugs, performance issues and security risks. Reference actual files and lines, suggest practical fixes, and distinguish potential issues from verified findings.",
    }
    for title, desc in descriptions.items():
        old = next((p for p in projects if p["project_name"] == title), None)
        if old:
            saved[title] = old["id"]
            continue
        body = {
            "project_name": title,
            "description": desc,
            "programming_language": "JavaScript"
            if title == "Node Code Review"
            else "Python",
            "framework": "Node.js"
            if title == "Node Code Review"
            else "React + FastAPI"
            if title == "E-commerce Studio"
            else "FastAPI",
            "application_type": "api"
            if title == "URL Shortener"
            else "web_application",
        }
        r = c.post("/api/projects", json=body)
        r.raise_for_status()
        saved[title] = r.json()["id"]
    (ROOT / ".local/demo-projects.json").write_text(json.dumps(saved, indent=2))
    print(json.dumps(saved, indent=2))
