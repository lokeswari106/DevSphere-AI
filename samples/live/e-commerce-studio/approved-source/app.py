"""Human-reviewed teaching slice derived from the recorded AI proposal.

SQLite and a seeded catalogue are for a local demo. Payments stay disabled.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="E-commerce teaching sample")
bearer = HTTPBearer(auto_error=False)
DB_PATH = os.getenv("DB_PATH", "ecommerce.db")


@contextmanager
def database():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, session_hash TEXT, session_expires INTEGER);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
          price_cents INTEGER NOT NULL CHECK(price_cents>0),stock INTEGER NOT NULL CHECK(stock>=0));
        CREATE TABLE IF NOT EXISTS cart_items(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),
          product_id INTEGER NOT NULL REFERENCES products(id),quantity INTEGER NOT NULL CHECK(quantity>0),UNIQUE(user_id,product_id));
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),
          total_cents INTEGER NOT NULL CHECK(total_cents>0),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),
          product_id INTEGER NOT NULL REFERENCES products(id),quantity INTEGER NOT NULL CHECK(quantity>0),price_cents INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS payment_intents(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),
          amount_cents INTEGER NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS orders_user_idx ON orders(user_id);
        CREATE INDEX IF NOT EXISTS order_items_order_idx ON order_items(order_id);
        ''')
        # Explicit classroom catalogue, not market or payment data.
        db.executemany("INSERT OR IGNORE INTO products VALUES(?,?,?,?)", [(1,"Notebook",1200,30),(2,"Desk lamp",3500,15),(3,"Canvas bag",1800,20)])


init_db()


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def email_shape(cls, value):
        value = value.strip().lower()
        if value.count("@") != 1 or "." not in value.split("@")[-1] or any(c.isspace() for c in value):
            raise ValueError("Enter a valid email address")
        return value


class CartInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


class PaymentInput(BaseModel):
    order_id: int = Field(gt=0)


def password_digest(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 300000).hex()


def get_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, "Sign in required")
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    with database() as db:
        user = db.execute("SELECT id FROM users WHERE session_hash=? AND session_expires>?", (token_hash, int(time.time()))).fetchone()
    if not user:
        raise HTTPException(401, "Invalid or expired session")
    return user["id"]


@app.post("/api/users", status_code=201)
def register_user(data: Credentials):
    salt = secrets.token_hex(16)
    try:
        with database() as db:
            cursor = db.execute("INSERT INTO users(email,password_hash) VALUES(?,?)", (data.email, salt+":"+password_digest(data.password,salt)))
            return {"id": cursor.lastrowid, "email": data.email}
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Email already registered")


@app.post("/api/users/login")
def login_user(data: Credentials):
    with database() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (data.email,)).fetchone()
        if not user:
            # Perform comparable work without revealing account existence.
            password_digest(data.password,"00"*16)
            raise HTTPException(401, "Invalid credentials")
        salt, stored = user["password_hash"].split(":",1)
        if not hmac.compare_digest(password_digest(data.password,salt),stored):
            raise HTTPException(401, "Invalid credentials")
        token = secrets.token_urlsafe(32)
        db.execute("UPDATE users SET session_hash=?,session_expires=? WHERE id=?", (hashlib.sha256(token.encode()).hexdigest(),int(time.time())+3600,user["id"]))
        return {"session_token": token,"user_id":user["id"]}


@app.get("/api/products")
def products():
    with database() as db:
        return [dict(r) for r in db.execute("SELECT * FROM products ORDER BY id")]


@app.post("/api/cart")
def add_to_cart(data: CartInput, user_id=Depends(get_user)):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        product = db.execute("SELECT stock FROM products WHERE id=?", (data.product_id,)).fetchone()
        if not product:
            raise HTTPException(404,"Product not found")
        old = db.execute("SELECT quantity FROM cart_items WHERE user_id=? AND product_id=?",(user_id,data.product_id)).fetchone()
        quantity = (old["quantity"] if old else 0) + data.quantity
        if quantity > product["stock"]:
            raise HTTPException(409,"Insufficient stock")
        db.execute("INSERT INTO cart_items(user_id,product_id,quantity) VALUES(?,?,?) ON CONFLICT(user_id,product_id) DO UPDATE SET quantity=excluded.quantity",(user_id,data.product_id,quantity))
    return {"message":"Cart updated"}


@app.get("/api/cart")
def cart(user_id=Depends(get_user)):
    with database() as db:
        return [dict(r) for r in db.execute("SELECT c.product_id,c.quantity,p.name,p.price_cents FROM cart_items c JOIN products p ON p.id=c.product_id WHERE c.user_id=?",(user_id,))]


@app.delete("/api/cart/{product_id}")
def remove(product_id: int,user_id=Depends(get_user)):
    with database() as db:
        db.execute("DELETE FROM cart_items WHERE user_id=? AND product_id=?",(user_id,product_id))
    return {"message":"Removed"}


@app.post("/api/orders",status_code=201)
def checkout(user_id=Depends(get_user)):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        items = db.execute("SELECT c.product_id,c.quantity,p.price_cents,p.stock FROM cart_items c JOIN products p ON p.id=c.product_id WHERE c.user_id=?",(user_id,)).fetchall()
        if not items:
            raise HTTPException(400,"Cart is empty")
        if any(r["stock"] < r["quantity"] for r in items):
            raise HTTPException(409,"Stock changed; update your cart")
        total = sum(r["price_cents"]*r["quantity"] for r in items)
        order_id = db.execute("INSERT INTO orders(user_id,total_cents) VALUES(?,?)",(user_id,total)).lastrowid
        for r in items:
            db.execute("UPDATE products SET stock=stock-? WHERE id=?",(r["quantity"],r["product_id"]))
            db.execute("INSERT INTO order_items(order_id,product_id,quantity,price_cents) VALUES(?,?,?,?)",(order_id,r["product_id"],r["quantity"],r["price_cents"]))
        db.execute("DELETE FROM cart_items WHERE user_id=?",(user_id,))
        return dict(db.execute("SELECT id,total_cents,created_at FROM orders WHERE id=?",(order_id,)).fetchone())


@app.get("/api/orders")
def orders(user_id=Depends(get_user)):
    with database() as db:
        return [dict(r) for r in db.execute("SELECT id,total_cents,created_at FROM orders WHERE user_id=? ORDER BY id DESC",(user_id,))]


@app.post("/api/payment")
def payment(data: PaymentInput,user_id=Depends(get_user)):
    with database() as db:
        order = db.execute("SELECT total_cents FROM orders WHERE id=? AND user_id=?",(data.order_id,user_id)).fetchone()
        if not order:
            raise HTTPException(404,"Order not found")
    # No fake provider success, transaction or card handling.
    raise HTTPException(503,"Payments disabled in this educational demo; no charge was attempted")


@app.post("/api/logout")
def logout(user_id=Depends(get_user)):
    with database() as db:
        db.execute("UPDATE users SET session_hash=NULL,session_expires=NULL WHERE id=?",(user_id,))
    return {"message":"Signed out"}
