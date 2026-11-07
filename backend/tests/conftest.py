import os, sys, json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend"))
# Dedicated database only. Never reset the demonstration database.
from dotenv import dotenv_values

values = dotenv_values(root / ".env")
os.environ["DATABASE_URL"] = (
    values["DATABASE_URL"].rsplit("/", 1)[0] + "/devsphere_test"
)
os.environ["WORKER_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "tests-only-secret-long-enough-not-for-production"
import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine, Session
from app import models
from app.main import create_app
from app.security import _attempts


@pytest.fixture(autouse=True)
def clean_database():
    assert engine.url.database == "devsphere_test"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _attempts.clear()
    yield


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def auth(client):
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Test Student",
            "email": "test@example.com",
            "password": "a-strong-test-password",
        },
    )
    assert r.status_code == 201, r.text
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return client


@pytest.fixture
def project(auth):
    r = auth.post(
        "/api/projects",
        json={
            "project_name": "Test project",
            "description": "Build a URL shortening application with validation and tests.",
            "programming_language": "Python",
            "framework": "FastAPI",
            "application_type": "api",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()
