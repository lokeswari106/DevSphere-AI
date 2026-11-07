import io, zipfile
import pytest
from app.db import Session
from app.models import GeneratedFile, Document, Run, AgentTask
from app.services.artifacts import latest_files, save_doc


def approve(client, pid, a):
    p = client.get("/api/projects/" + pid).json()
    return client.post(
        f"/api/projects/{pid}/approvals/{a['id']}/decision",
        json={
            "decision": "approve",
            "artifact_hash": a["artifact_hash"],
            "expected_revision": p["revision"],
        },
    )


def import_source(client, pid, content="def add(a,b): return a+b"):
    p = client.get("/api/projects/" + pid).json()
    return client.post(
        f"/api/projects/{pid}/files/import",
        json={
            "files": [{"path": "app.py", "content": content}],
            "expected_revision": p["revision"],
        },
    )


def test_registration_without_invitation_and_hash_not_exposed(client):
    r = client.post(
        "/api/auth/register",
        json={
            "name": "New Student",
            "email": "new@example.com",
            "password": "long-test-password",
        },
    )
    assert r.status_code == 201
    assert "password_hash" not in r.text
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert client.get("/api/auth/me").status_code == 200


def test_auth_csrf_and_origin(auth, project):
    auth.headers.pop("X-CSRF-Token")
    assert auth.post("/api/projects", json={}).status_code == 403
    assert (
        auth.post(
            "/api/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"email": "test@example.com", "password": "a-strong-test-password"},
        ).status_code
        == 403
    )


def test_bearer_auth_no_cookie(client):
    r = client.post(
        "/api/auth/register",
        json={
            "name": "API Student",
            "email": "api@example.com",
            "password": "long-test-password",
        },
    )
    token = r.json()["access_token"]
    client.cookies.clear()
    client.headers["Authorization"] = "Bearer " + token
    assert client.get("/api/auth/me").status_code == 200


def test_cross_owner_rejected(auth, project):
    r = auth.post(
        "/api/auth/register",
        json={
            "name": "Other Student",
            "email": "other@example.com",
            "password": "another-long-password",
        },
    )
    auth.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    for suffix in [
        "",
        "/workflow",
        "/files",
        "/approvals",
        "/documents",
        "/export",
        "/reviews",
        "/tests",
        "/versions",
    ]:
        assert auth.get("/api/projects/" + project["id"] + suffix).status_code == 404


def test_versioned_changes_require_hash_bound_approval(auth, project):
    pid = project["id"]
    r = import_source(auth, pid)
    assert r.status_code == 202, r.text
    a = r.json()
    assert auth.get(f"/api/projects/{pid}/files").json() == []
    assert approve(auth, pid, a).status_code == 200
    f = auth.get(f"/api/projects/{pid}/files").json()[0]
    p = auth.get("/api/projects/" + pid).json()
    r = auth.put(
        f"/api/projects/{pid}/files/{f['id']}",
        json={
            "content": "def add(a,b):\n    return a+b+1",
            "expected_revision": p["revision"],
        },
    )
    a2 = r.json()
    wrong = {**a2, "artifact_hash": "0" * 64}
    assert approve(auth, pid, wrong).status_code == 409
    assert approve(auth, pid, a2).status_code == 200
    assert approve(auth, pid, a2).status_code == 409
    current = auth.get(f"/api/projects/{pid}/files").json()[0]
    assert current["version"] == 2
    diff = auth.get(f"/api/projects/{pid}/files/{current['id']}/diff?against=1").json()
    assert "return a+b+1" in diff["diff"]
    with Session() as db:
        assert len(db.query(GeneratedFile).all()) == 2


@pytest.mark.parametrize(
    "path",
    [
        "../secret.py",
        "/root.py",
        "a/../b.py",
        "a\\b.py",
        ".env",
        "node_modules/x.js",
        "foo/./x.py",
        "C:/x.py",
        "bad.exe",
    ],
)
def test_upload_path_boundaries(auth, project, path):
    r = auth.post(
        f"/api/projects/{project['id']}/files/import",
        json={"files": [{"path": path, "content": "test"}], "expected_revision": 1},
    )
    assert r.status_code == 422, r.text


def test_duplicate_file_and_secret_rejected(auth, project):
    r = auth.post(
        f"/api/projects/{project['id']}/files/import",
        json={
            "files": [
                {"path": "x.py", "content": "a"},
                {"path": "X.py", "content": "b"},
            ],
            "expected_revision": 1,
        },
    )
    assert r.status_code == 422
    r = import_source(auth, project["id"], "-----BEGIN PRIVATE KEY-----")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_only_one_active_workflow_and_cancel(auth, project, monkeypatch):
    import asyncio
    from sqlalchemy import select
    from app.models import AgentExecution
    from app.services.orchestration import dispatcher
    from app.services.provider import provider

    entered, interrupted, stop = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def waiting_provider(*args):
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            interrupted.set()
            raise

    monkeypatch.setattr(provider, "generate", waiting_provider)
    path = f"/api/projects/{project['id']}"
    assert (
        auth.post(path + "/execute", json={"workflow_type": "full"}).status_code == 202
    )
    assert (
        auth.post(path + "/execute", json={"workflow_type": "full"}).status_code == 409
    )
    worker = asyncio.create_task(dispatcher(stop))
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        assert auth.post(path + "/cancel").status_code == 200
        await asyncio.wait_for(interrupted.wait(), timeout=5)
        w = auth.get(path + "/workflow").json()
        assert w["run"]["status"] == "cancelled"
        assert w["tasks"][0]["task_status"] == "cancelled"
        with Session() as db:
            executions = db.scalars(select(AgentExecution)).all()
            assert len(executions) == 1
            assert executions[0].execution_status == "cancelled"
    finally:
        stop.set()
        await worker


def test_prerequisites_and_stack_validation(auth, project):
    assert auth.post(f"/api/projects/{project['id']}/design").status_code == 409
    assert (
        auth.post(
            "/api/projects",
            json={
                **{
                    k: project[k]
                    for k in [
                        "project_name",
                        "description",
                        "programming_language",
                        "framework",
                        "application_type",
                    ]
                },
                "framework": "Node.js",
            },
        ).status_code
        == 422
    )


def test_export_only_approved_files(auth, project):
    pid = project["id"]
    a = import_source(auth, pid).json()
    before = zipfile.ZipFile(
        io.BytesIO(auth.get(f"/api/projects/{pid}/export").content)
    )
    assert "app.py" not in before.namelist()
    approve(auth, pid, a)
    after = zipfile.ZipFile(io.BytesIO(auth.get(f"/api/projects/{pid}/export").content))
    assert "app.py" in after.namelist()
    assert ".env" not in after.namelist()


def test_test_execution_cannot_start_without_approval(auth, project):
    pid = project["id"]
    approve(auth, pid, import_source(auth, pid).json())
    r = auth.post(f"/api/projects/{pid}/run-tests", json={"recipe": "python"})
    assert r.status_code == 202
    assert auth.get(f"/api/projects/{pid}/tests").json() == []
    assert approve(auth, pid, r.json()).status_code == 200
    tests = auth.get(f"/api/projects/{pid}/tests").json()
    assert tests[0]["test_status"] == "queued" and tests[0]["total_tests"] is None


def test_confirm_delete_and_stale_edit(auth, project):
    pid = project["id"]
    assert (
        auth.delete(
            f"/api/projects/{pid}", params={"confirm_name": "wrong"}
        ).status_code
        == 409
    )
    assert (
        auth.put(
            f"/api/projects/{pid}",
            json={
                "project_name": "Updated",
                "description": "A sufficiently long updated requirement description.",
                "expected_revision": 99,
            },
        ).status_code
        == 409
    )
    assert (
        auth.delete(
            f"/api/projects/{pid}", params={"confirm_name": project["project_name"]}
        ).status_code
        == 204
    )
    assert auth.get(f"/api/projects/{pid}").status_code == 404


def test_document_pdf(auth, project):
    from app.models import Project

    with Session() as db:
        p = db.get(Project, project["id"])
        d = save_doc(
            db, p, "requirements", {"summary": "Test requirement", "items": ["A", "B"]}
        )
        db.commit()
        did = d.id
    r = auth.get(f"/api/projects/{project['id']}/documents/{did}/download?format=pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_rate_limit(client):
    for _ in range(10):
        client.post(
            "/api/auth/login", json={"email": "none@example.com", "password": "wrong"}
        )
    assert (
        client.post(
            "/api/auth/login", json={"email": "none@example.com", "password": "wrong"}
        ).status_code
        == 429
    )
