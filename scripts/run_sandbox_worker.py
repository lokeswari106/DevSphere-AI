"""Separate trusted worker. Never import this from the FastAPI application."""

import sys, time, signal, threading, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import select, delete
from app.db import Session
from app.models import TestResult, Run, Project, AuditEvent, now
from app.services.artifacts import event, propose
from app.services.sandbox import execute_snapshot, available
from datetime import timedelta

stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *_: stop.set())
signal.signal(signal.SIGINT, lambda *_: stop.set())
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, lambda *_: stop.set())
stop_file = os.environ.get("DEVSPHERE_STOP_FILE")


def heartbeats():
    while not stop.is_set():
        if stop_file and Path(stop_file).exists():
            stop.set()
            return
        try:
            with Session() as db:
                db.execute(
                    delete(AuditEvent).where(
                        AuditEvent.event_type == "runner_heartbeat"
                    )
                )
                db.add(
                    AuditEvent(
                        event_type="runner_heartbeat",
                        event_data={
                            "image_ready": available(),
                            "recipes": ["python", "node", "java"],
                        },
                    )
                )
                db.commit()
        except Exception as e:
            print("Runner heartbeat:", type(e).__name__, flush=True)
        stop.wait(10)


threading.Thread(target=heartbeats, daemon=True).start()
with Session() as db:
    for t in db.scalars(select(TestResult).where(TestResult.test_status == "running")):
        t.test_status = "interrupted"
        t.execution_output += "\nRunner restarted before an outcome was recorded."
        if t.run_id:
            r = db.get(Run, t.run_id)
            r.status = "failed"
            r.error = "Sandbox execution interrupted. Retry requires approval."
    db.commit()
print("DevSphere isolated test worker ready.", flush=True)
while not stop.is_set():
    with Session() as db:
        t = db.scalar(
            select(TestResult)
            .where(TestResult.test_status == "queued")
            .order_by(TestResult.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not t:
            stop.wait(2)
            continue
        t.test_status = "running"
        tid = t.id
        files = t.details["files"]
        recipe = t.recipe
        db.commit()
    try:
        result = execute_snapshot(files, recipe)
    except Exception as exc:
        result = {
            "status": "runner_error",
            "log": f"{type(exc).__name__}: {str(exc)[:600]}",
            "total": None,
            "passed": None,
            "failed": None,
        }
    with Session() as db:
        t = db.get(TestResult, tid)
        if t.test_status == "cancelled":
            continue
        t.test_status = result["status"]
        t.total_tests = result.get("total")
        t.passed_tests = result.get("passed")
        t.failed_tests = result.get("failed")
        t.execution_output = result["log"]
        t.details = {
            **t.details,
            "execution": {k: v for k, v in result.items() if k != "log"},
            "completed_at": now().isoformat(),
        }
        event(
            db,
            t.project_id,
            "tests_completed",
            {"test_id": t.id, "status": t.test_status, "source_hash": t.source_hash},
        )
        if t.run_id:
            r = db.get(Run, t.run_id)
            p = db.get(Project, t.project_id)
            if r.status == "testing":
                if t.test_status == "passed":
                    r.stage += 1
                    r.status = "queued"
                    p.project_status = "working"
                else:
                    propose(
                        db,
                        p,
                        "test_failure",
                        {
                            "test_id": t.id,
                            "status": t.test_status,
                            "source_hash": t.source_hash,
                            "summary": "Tests did not pass. Request a repair or explicitly continue with these limitations.",
                        },
                        r.id,
                    )
                    r.status = "awaiting_approval"
                    p.project_status = "needs_attention"
        db.commit()
    print("Sandbox execution", tid, result["status"], flush=True)
