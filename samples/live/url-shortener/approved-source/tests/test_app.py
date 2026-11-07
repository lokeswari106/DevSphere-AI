"""Real model test proposal corrected during recorded human review."""
import pytest
from fastapi.testclient import TestClient
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "db_path", str(tmp_path / "links.db"))
    app_module.init_db()
    with TestClient(app_module.app) as c:
        yield c


def test_create_short_link(client):
    response = client.post("/links", json={"url": "https://example.com/path10"})
    assert response.status_code == 201
    code = response.json()["short_code"]
    assert code and code != "https://example.com/path10"
    stats = client.get(f"/links/{code}")
    assert stats.status_code == 200
    assert stats.json() == {"original_url": "https://example.com/path10", "click_count": 0}


def test_redirect_with_click_increment(client):
    created = client.post("/links", json={"url": "https://example.com/path11"})
    assert created.status_code == 201
    code = created.json()["short_code"]
    for count in [1, 2]:
        response = client.get(f"/r/{code}", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/path11"
        assert client.get(f"/links/{code}").json()["click_count"] == count


def test_missing_code_returns_404(client):
    for path in ["/r/missing", "/links/missing"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 404
        assert response.json() == {"detail": "Code not found"}


def test_invalid_url_rejected(client):
    for url in ["javascript:alert(1)", "ftp://example.com", "http://127.0.0.1/",
                "https://10.0.0.1/", "http://[::1]/", "http://localhost/",
                "https://user:password@example.com/", "http://example.com:99999/"]:
        assert client.post("/links", json={"url": url}).status_code == 422
    assert client.post("/links", json={}).status_code == 422


def test_collision_exhaustion(client, monkeypatch):
    calls = []
    def same_code(size):
        calls.append(size)
        return "collision"
    monkeypatch.setattr(app_module.secrets, "token_urlsafe", same_code)
    first = client.post("/links", json={"url": "https://example.com/first"})
    assert first.status_code == 201
    calls.clear()
    second = client.post("/links", json={"url": "https://example.com/second"})
    assert second.status_code == 503
    assert second.json() == {"detail": "Five code-collision attempts exhausted"}
    assert len(calls) == 5
    assert client.get("/links/collision").json() == {"original_url":"https://example.com/first", "click_count":0}
