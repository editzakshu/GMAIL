import os
import sqlite3
import secrets
from pathlib import Path
from flask import Flask, render_template, request, make_response

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("MAILQR_DB_PATH", BASE_DIR / "mailqr_stats.sqlite3"))
TRACKED_KEYS = ("to", "cc", "bcc", "subject", "body")
VISITOR_COOKIE = "mailqr_visitor"

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS link_opens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT NOT NULL,
                opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_link_opens_visitor ON link_opens(visitor_id)")

def has_email_payload():
    # Count visits to generated share links, not ordinary visits to the homepage.
    return any(request.args.get(key, "").strip() for key in TRACKED_KEYS)

def record_link_open():
    visitor_id = request.cookies.get(VISITOR_COOKIE)
    is_new_cookie = not visitor_id
    if is_new_cookie:
        visitor_id = secrets.token_urlsafe(24)
    with connect_db() as conn:
        conn.execute("INSERT INTO link_opens(visitor_id) VALUES (?)", (visitor_id,))
    return visitor_id, is_new_cookie

def get_stats():
    with connect_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM link_opens").fetchone()[0]
        unique = conn.execute("SELECT COUNT(DISTINCT visitor_id) FROM link_opens").fetchone()[0]
    return {"total_opens": total, "unique_visitors": unique}

init_db()

@app.get("/")
def index():
    values = {key: request.args.get(key, "") for key in TRACKED_KEYS}
    tracked = has_email_payload()
    visitor_id = None
    is_new_cookie = False
    if tracked:
        visitor_id, is_new_cookie = record_link_open()
    response = make_response(render_template(
        "index.html", values=values, stats=get_stats(), tracked_link=tracked
    ))
    if tracked and is_new_cookie:
        response.set_cookie(
            VISITOR_COOKIE, visitor_id, max_age=60*60*24*365,
            httponly=True, samesite="Lax", secure=request.is_secure
        )
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
