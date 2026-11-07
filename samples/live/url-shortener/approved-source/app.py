"""AI draft with recorded review fixes: validation, initialization and DB lifetime."""
import os
import secrets
import sqlite3
import ipaddress
from contextlib import contextmanager
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

app = FastAPI(title="URL Shortener teaching API")
db_path = os.getenv("DB_PATH", "shortener.db")

@contextmanager
def database():
    db = sqlite3.connect(db_path, timeout=10)
    try:
        with db:
            yield db
    finally:
        db.close()

def init_db():
    with database() as db:
        db.execute("CREATE TABLE IF NOT EXISTS Link(short_code TEXT PRIMARY KEY, original_url TEXT NOT NULL, click_count INTEGER NOT NULL DEFAULT 0 CHECK(click_count>=0))")

init_db()

class URLRequest(BaseModel):
    url: str = Field(min_length=8,max_length=2048)

def validate_url(url):
    if any(ch.isspace() or ord(ch)<32 for ch in url):
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").rstrip(".").lower()
        if parsed.scheme not in {"http","https"} or not host or parsed.username is not None or parsed.password is not None:
            return False
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return False
        if host == "localhost" or host.endswith(".localhost"):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return "." in host and not host.split(".")[-1].isdigit()
    except ValueError:
        return False

@app.post("/links",status_code=201)
def create_link(request: URLRequest):
    if not validate_url(request.url):
        raise HTTPException(422,"Use a public HTTP(S) destination without credentials")
    for _ in range(5):
        code = secrets.token_urlsafe(6)
        try:
            with database() as db:
                db.execute("INSERT INTO Link(short_code,original_url) VALUES(?,?)",(code,request.url))
            return {"short_code":code}
        except sqlite3.IntegrityError:
            continue
    raise HTTPException(503,"Five code-collision attempts exhausted")

@app.get("/r/{code}")
def redirect(code: str):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT original_url FROM Link WHERE short_code=?",(code,)).fetchone()
        if row is None:
            raise HTTPException(404,"Code not found")
        db.execute("UPDATE Link SET click_count=click_count+1 WHERE short_code=?",(code,))
        return RedirectResponse(row[0],status_code=307)

@app.get("/links/{code}")
def get_stats(code: str):
    with database() as db:
        row = db.execute("SELECT original_url,click_count FROM Link WHERE short_code=?",(code,)).fetchone()
        if row is None:
            raise HTTPException(404,"Code not found")
        return {"original_url":row[0],"click_count":row[1]}
