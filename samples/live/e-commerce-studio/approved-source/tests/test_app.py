"""Human review checklist as executable tests against the actual generated module.

This file is staged for proposal review, never executed on the application host.
"""
import hashlib
import time
import pytest
from fastapi.testclient import TestClient
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "shop.db"))
    app_module.init_db()
    with TestClient(app_module.app) as c:
        yield c


def account(client, email="student@example.com"):
    credentials = {"email": email, "password": "Classroom-pass-2026"}
    response = client.post("/api/users", json=credentials)
    assert response.status_code == 201
    user_id = response.json()["id"]
    response = client.post("/api/users/login", json=credentials)
    assert response.status_code == 200
    token = response.json()["session_token"]
    return {"Authorization": "Bearer " + token}, user_id, token


def test_registration_password_storage_and_duplicates(client):
    headers, user_id, token = account(client)
    with app_module.database() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        assert "Classroom-pass-2026" not in user["password_hash"]
        assert len(user["password_hash"].split(":")) == 2
        assert user["session_hash"] == hashlib.sha256(token.encode()).hexdigest()
        assert user["session_expires"] > int(time.time())
    assert client.post("/api/users", json={"email":"student@example.com", "password":"Classroom-pass-2026"}).status_code == 409
    assert client.post("/api/users", json={"email":"broken", "password":"short"}).status_code == 422


def test_login_unauthorized_and_expiry(client):
    assert client.get("/api/cart").status_code == 401
    assert client.get("/api/orders", headers={"Authorization":"Bearer bad"}).status_code == 401
    headers, user_id, token = account(client)
    assert client.post("/api/users/login", json={"email":"student@example.com", "password":"Incorrect-password"}).status_code == 401
    with app_module.database() as db:
        db.execute("UPDATE users SET session_expires=? WHERE id=?", (int(time.time())-1, user_id))
    assert client.get("/api/cart", headers=headers).status_code == 401


def test_cart_validation_and_removal(client):
    h, _, _ = account(client)
    assert client.post("/api/cart", headers=h, json={"product_id":1,"quantity":0}).status_code == 422
    assert client.post("/api/cart", headers=h, json={"product_id":999,"quantity":1}).status_code == 404
    assert client.post("/api/cart", headers=h, json={"product_id":1,"quantity":31}).status_code == 409
    for quantity in [1,2]:
        assert client.post("/api/cart", headers=h, json={"product_id":1,"quantity":quantity}).status_code == 200
    assert client.get("/api/cart", headers=h).json()[0]["quantity"] == 3
    assert client.delete("/api/cart/1", headers=h).status_code == 200
    assert client.get("/api/cart", headers=h).json() == []


def test_checkout_server_totals_stock_and_cart_clear(client):
    h, _, _ = account(client)
    assert client.post("/api/orders", headers=h).status_code == 400
    assert client.post("/api/cart", headers=h, json={"product_id":1,"quantity":2}).status_code == 200
    assert client.post("/api/cart", headers=h, json={"product_id":2,"quantity":1}).status_code == 200
    response = client.post("/api/orders", headers=h, json={"total_cents":1})
    assert response.status_code == 201
    order = response.json()
    assert order["total_cents"] == 2*1200+3500
    products = {p["id"]:p for p in client.get("/api/products").json()}
    assert products[1]["stock"] == 28 and products[2]["stock"] == 14
    assert client.get("/api/cart", headers=h).json() == []
    assert client.get("/api/orders", headers=h).json()[0]["id"] == order["id"]


def test_stock_changed_transaction_rolls_back(client):
    h, _, _ = account(client)
    for product_id in [1,2]:
        assert client.post("/api/cart", headers=h, json={"product_id":product_id,"quantity":2}).status_code == 200
    with app_module.database() as db:
        db.execute("UPDATE products SET stock=0 WHERE id=2")
    assert client.post("/api/orders", headers=h).status_code == 409
    assert client.get("/api/orders", headers=h).json() == []
    assert len(client.get("/api/cart", headers=h).json()) == 2
    assert client.get("/api/products").json()[0]["stock"] == 30
    with app_module.database() as db:
        assert db.execute("SELECT COUNT(*) FROM order_items").fetchone()[0] == 0


def test_user_isolation_and_payments_disabled(client):
    alice, _, _ = account(client, "alice@example.com")
    bob, _, _ = account(client, "bob@example.com")
    assert client.post("/api/cart", headers=alice, json={"product_id":1,"quantity":1}).status_code == 200
    assert client.get("/api/cart", headers=bob).json() == []
    assert client.delete("/api/cart/1", headers=bob).status_code == 200
    assert len(client.get("/api/cart", headers=alice).json()) == 1
    order = client.post("/api/orders", headers=alice).json()
    assert client.get("/api/orders", headers=bob).json() == []
    assert client.post("/api/payment", headers=bob, json={"order_id":order["id"]}).status_code == 404
    response = client.post("/api/payment", headers=alice, json={"order_id":order["id"]})
    assert response.status_code == 503 and "no charge" in response.json()["detail"]
    with app_module.database() as db:
        assert db.execute("SELECT COUNT(*) FROM payment_intents").fetchone()[0] == 0


def test_logout_revokes_session(client):
    h, _, _ = account(client)
    assert client.post("/api/logout", headers=h).status_code == 200
    assert client.get("/api/cart", headers=h).status_code == 401
