import pytest
from unittest.mock import AsyncMock
from sqlalchemy import select
from app.db import Session
from app.models import Run, Project, Approval, AgentTask, AgentExecution, Document
from app.services.orchestration import advance, perform, ROUTES
from app.services.provider import provider
from test_agents import FIXTURES
from test_api import approve, import_source


@pytest.mark.asyncio
async def test_quick_review_inspects_uploaded_source_and_persists_replacement(auth, project, monkeypatch):
    pid = project["id"]
    assert auth.post(f"/api/projects/{pid}/execute", json={"workflow_type":"quick_review"}).status_code == 409
    approve(auth, pid, import_source(auth, pid).json())
    response = auth.post(f"/api/projects/{pid}/execute", json={"workflow_type":"quick_review"})
    assert response.status_code == 202
    seen = []
    async def fake(prompt, context, schema):
        seen.append(context)
        return {"summary":"Fixture review", "limitations":["Automated test fixture"], "findings":[{
            "file_path":"app.py", "line_number":1, "severity":"medium", "issue_type":"correctness",
            "description":"Fixture finding", "suggested_fix":"Replace the function", "improved_code":"def answer():\n    return 42\n",
        }]}, {"provider":"test_fixture"}
    monkeypatch.setattr(provider,"generate",fake)
    with Session() as db:
        run=db.get(Run,response.json()["run_id"]); run.status="running"; db.commit()
    await advance(response.json()["run_id"])
    workflow=auth.get(f"/api/projects/{pid}/workflow").json()
    assert workflow["run"]["status"] == "completed"
    assert {t["task_name"] for t in workflow["tasks"]} == {"review","security"}
    assert not workflow["approvals"]
    assert all(c["files"] and c["files"][0]["path"]=="app.py" for c in seen)
    findings=auth.get(f"/api/projects/{pid}/reviews").json()
    assert len(findings)==2 and all(f["improved_code"] and f["source_current"] for f in findings)
    assert auth.get(f"/api/projects/{pid}/tests").json() == []


@pytest.mark.asyncio
async def test_test_syntax_failure_retries_with_original_draft(auth, project, monkeypatch):
    pid=project["id"]
    approve(auth,pid,import_source(auth,pid).json())
    response=auth.post(f"/api/projects/{pid}/execute",json={"workflow_type":"tests"}).json()
    invalid={**FIXTURES["tests"],"files":[{"path":"tests/test_app.py","content":"def test_bad():\n assert True)"}]}
    fake=AsyncMock(side_effect=[(invalid,{}),(FIXTURES["tests"],{"provider":"test_fixture"})])
    monkeypatch.setattr(provider,"generate",fake)
    with Session() as db:
        run=db.get(Run,response["run_id"]); run.status="running"; db.commit()
    result=await perform(response["run_id"],"tests")
    assert result["status"]=="completed" and fake.await_count==2
    second_context=fake.call_args_list[1].args[1]
    assert second_context["previous_invalid_artifact"]==invalid
    assert "SyntaxError" in second_context["validation_feedback"]


@pytest.mark.asyncio
async def test_full_pipeline_waits_for_human_at_requirements(
    auth, project, monkeypatch
):
    pid = project["id"]
    r = auth.post(f"/api/projects/{pid}/execute", json={"workflow_type": "full"}).json()

    async def fake(prompt, ctx, schema):
        return FIXTURES[
            "orchestrator" if ctx["assignment"] == "plan" else ctx["assignment"]
        ], {"provider": "test_fixture"}

    monkeypatch.setattr(provider, "generate", fake)
    with Session() as db:
        run = db.get(Run, r["run_id"])
        run.status = "running"
        db.commit()
    await advance(r["run_id"])
    w = auth.get(f"/api/projects/{pid}/workflow").json()
    assert w["run"]["status"] == "awaiting_approval"
    assert w["approvals"][0]["checkpoint"] == "plan"
    assert approve(auth, pid, w["approvals"][0]).status_code == 200
    with Session() as db:
        run = db.get(Run, r["run_id"])
        assert run.stage == 1
        run.status = "running"
        db.commit()
    await advance(r["run_id"])
    w = auth.get(f"/api/projects/{pid}/workflow").json()
    assert w["run"]["status"] == "awaiting_approval"
    assert auth.get(f"/api/projects/{pid}/requirements").json() == []
    assert approve(auth, pid, w["approvals"][0]).status_code == 200
    assert auth.get(f"/api/projects/{pid}/requirements").json()[0]["version"] == 1
    assert auth.get(f"/api/projects/{pid}/workflow").json()["run"]["stage"] == 2


@pytest.mark.asyncio
async def test_provider_retry_records_actual_attempts(auth, project, monkeypatch):
    pid = project["id"]
    r = auth.post(f"/api/projects/{pid}/execute", json={"workflow_type": "full"}).json()
    fake = AsyncMock(
        side_effect=[
            ValueError("invalid JSON"),
            (FIXTURES["orchestrator"], {"provider": "test_fixture"}),
        ]
    )
    monkeypatch.setattr(provider, "generate", fake)
    with Session() as db:
        run = db.get(Run, r["run_id"])
        run.status = "running"
        db.commit()
    result = await perform(r["run_id"], "plan")
    assert result["status"] == "completed"
    assert fake.await_count == 2
    with Session() as db:
        ex = db.scalars(
            select(AgentExecution).order_by(AgentExecution.created_at)
        ).all()
        assert [e.execution_status for e in ex] == ["failed", "completed"]
        assert ex[1].retry_count == 1
        assert db.get(AgentTask, result["task_id"]).error_message is None


@pytest.mark.asyncio
async def test_review_only_skips_generation_and_barrier(auth, project, monkeypatch):
    pid = project["id"]
    approve(auth, pid, import_source(auth, pid).json())
    r = auth.post(f"/api/projects/{pid}/review").json()
    assert ROUTES["review"] == ["plan", "quality", "documentation", "delivery"]

    async def fake(prompt, ctx, schema):
        return FIXTURES[ctx["assignment"]], {"provider": "test_fixture"}

    monkeypatch.setattr(provider, "generate", fake)
    with Session() as db:
        run = db.get(Run, r["run_id"])
        run.status = "running"
        run.stage = 1
        db.commit()
    await advance(r["run_id"])
    w = auth.get(f"/api/projects/{pid}/workflow").json()
    assert {t["task_name"] for t in w["tasks"]} == {"review", "security"}
    assert w["run"]["stage"] == 2
    with Session() as db:
        tasks = db.scalars(select(AgentTask)).all()
        assert tasks[0].input_data["source_hash"] == tasks[1].input_data["source_hash"]


@pytest.mark.asyncio
async def test_failed_provider_does_not_make_up_output(auth, project, monkeypatch):
    r = auth.post(
        f"/api/projects/{project['id']}/execute", json={"workflow_type": "full"}
    ).json()
    monkeypatch.setattr(
        provider, "generate", AsyncMock(side_effect=ValueError("provider unavailable"))
    )
    with Session() as db:
        run = db.get(Run, r["run_id"])
        run.status = "running"
        db.commit()
    await advance(r["run_id"])
    w = auth.get(f"/api/projects/{project['id']}/workflow").json()
    assert w["run"]["status"] == "failed"
    assert not w["approvals"]
    assert w["tasks"][0]["output_data"] == {}


@pytest.mark.asyncio
async def test_expired_lease_marks_interrupted_work_and_recovers(
    auth, project, monkeypatch
):
    import asyncio
    from datetime import timedelta
    from app.models import now
    from app.services import orchestration

    stop = asyncio.Event()
    seen = []
    r = auth.post(
        f"/api/projects/{project['id']}/execute", json={"workflow_type": "full"}
    ).json()
    with Session() as db:
        run = db.get(Run, r["run_id"])
        run.status = "running"
        run.lease_until = now() - timedelta(seconds=70)
        task = AgentTask(
            project_id=project["id"],
            run_id=run.id,
            agent_name="orchestrator",
            task_name="plan",
            task_status="running",
        )
        db.add(task)
        db.flush()
        execution = AgentExecution(
            project_id=project["id"], agent_task_id=task.id, execution_status="running"
        )
        db.add(execution)
        db.commit()
        tid = task.id
        eid = execution.id

    async def recovered(rid):
        seen.append(rid)
        stop.set()

    monkeypatch.setattr(orchestration, "advance", recovered)
    await asyncio.wait_for(orchestration.dispatcher(stop), 5)
    assert seen == [r["run_id"]]
    with Session() as db:
        assert db.get(AgentTask, tid).task_status == "interrupted"
        assert db.get(AgentExecution, eid).execution_status == "interrupted"
