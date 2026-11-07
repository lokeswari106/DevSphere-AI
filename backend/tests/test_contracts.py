from app.db import Session
from app.models import Project, Document, Approval
from app.services.artifacts import save_doc, propose
from sqlalchemy import select
from test_api import approve
from test_agents import FIXTURES


def test_openapi_has_responses_and_auth(client):
    from openapi_spec_validator import validate

    spec = client.get("/openapi.json").json()
    validate(spec)
    get = spec["paths"]["/api/projects/{project_id}"]["get"]
    assert get["security"] == [{"BearerAuth": []}]
    assert get["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("ProjectResponse")
    assert (
        "password_hash"
        not in spec["components"]["schemas"]["UserResponse"]["properties"]
    )


def test_edit_proposal_changes_hash_and_rejects_stale_approval(auth, project):
    pid = project["id"]
    with Session() as db:
        p = db.get(Project, pid)
        a = propose(db, p, "requirements", FIXTURES["requirements"])
        db.commit()
        aid = a.id
        old = a.artifact_hash
    new = {**FIXTURES["requirements"], "summary": "A revised user-approved brief"}
    r = auth.put(
        f"/api/projects/{pid}/approvals/{aid}",
        json={"expected_revision": 1, "artifact_hash": old, "payload": new},
    )
    assert r.status_code == 200, r.text
    assert r.json()["artifact_hash"] != old
    assert (
        auth.post(
            f"/api/projects/{pid}/approvals/{aid}/decision",
            json={"decision": "approve", "expected_revision": 1, "artifact_hash": old},
        ).status_code
        == 409
    )
    assert approve(auth, pid, r.json()).status_code == 200


def test_brief_change_invalidates_requirements_and_dependents(auth, project):
    pid = project["id"]
    with Session() as db:
        p = db.get(Project, pid)
        for kind in [
            "plan",
            "requirements",
            "architecture",
            "database",
            "documentation",
        ]:
            save_doc(db, p, kind, {"summary": "Old version"})
        db.commit()
    r = auth.put(
        f"/api/projects/{pid}",
        json={
            "project_name": project["project_name"],
            "description": "A changed requirement with different acceptance criteria.",
            "expected_revision": 1,
        },
    )
    assert r.status_code == 200
    assert auth.get(f"/api/projects/{pid}/documents").json() == []
    assert len(auth.get(f"/api/projects/{pid}/documents?history=true").json()) == 5


def test_delivery_regeneration_reexecutes_documentation(auth, project):
    from app.models import Run, AgentTask
    from app.services.orchestration import ROUTES

    pid = project["id"]
    with Session() as db:
        p = db.get(Project, pid)
        r = Run(
            project_id=pid,
            workflow_type="documentation",
            stage=2,
            status="awaiting_approval",
        )
        db.add(r)
        db.flush()
        task = AgentTask(
            project_id=pid,
            run_id=r.id,
            agent_name="testing_documentation",
            task_name="documentation",
            task_status="completed",
        )
        db.add(task)
        a = propose(db, p, "delivery", {"summary": "Review final report"}, r.id)
        db.commit()
        aid = a.id
        sha = a.artifact_hash
        tid = task.id
        rid = r.id
    response = auth.post(
        f"/api/projects/{pid}/approvals/{aid}/decision",
        json={
            "decision": "regenerate",
            "artifact_hash": sha,
            "expected_revision": 1,
            "comment": "Include the exact failed test details.",
        },
    )
    assert response.status_code == 200
    with Session() as db:
        r = db.get(Run, rid)
        assert ROUTES[r.workflow_type][r.stage] == "documentation"
        assert (
            r.request["stage_instructions"]["documentation"]
            == "Include the exact failed test details."
        )
        assert db.get(AgentTask, tid).task_status == "superseded"


def test_final_report_export_excludes_other_documents(auth, project):
    with Session() as db:
        p = db.get(Project, project["id"])
        d = save_doc(
            db,
            p,
            "documentation",
            {
                "final_report_markdown": "# Final report\nRequired findings only.",
                "readme_markdown": "# Installation\nUNRELATED SETUP TEXT",
            },
        )
        db.commit()
        did = d.id
    base = f"/api/projects/{project['id']}/documents/{did}/download"
    r = auth.get(base + "?format=md")
    assert r.status_code == 200
    assert "Required findings only" in r.text and "UNRELATED SETUP TEXT" not in r.text
    r = auth.get(base + "?format=md&section=readme")
    assert "UNRELATED SETUP TEXT" in r.text
