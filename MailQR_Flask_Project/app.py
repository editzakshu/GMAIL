
import os
import sqlite3
import secrets
from pathlib import Path
from urllib.parse import urlencode, quote

import qrcode
import streamlit as st

# -----------------------------
# Streamlit configuration
# -----------------------------
st.set_page_config(
    page_title="MailQR Analytics",
    page_icon="📧",
    layout="centered",
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(
    os.environ.get("MAILQR_DB_PATH", str(BASE_DIR / "mailqr_stats.sqlite3"))
)

# Set APP_URL in your hosting environment or Streamlit secrets
APP_URL = os.environ.get("APP_URL", "").strip()
try:
    APP_URL = st.secrets.get("APP_URL", APP_URL).strip()
except Exception:
    pass

TRACKED_KEYS = ("to", "cc", "bcc", "subject", "body")


# -----------------------------
# Database and analytics
# -----------------------------
def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
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
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_link_opens_visitor
            ON link_opens(visitor_id)
        """)


def get_stats():
    with connect_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM link_opens"
        ).fetchone()[0]
        unique = conn.execute(
            "SELECT COUNT(DISTINCT visitor_id) FROM link_opens"
        ).fetchone()[0]
    return total, unique


def record_open_once_per_session():
    """Count a share-link visit once per Streamlit browser session."""
    if st.session_state.get("_mailqr_counted_this_session", False):
        return

    visitor_id = st.session_state.get("_mailqr_visitor_id")
    if not visitor_id:
        visitor_id = secrets.token_urlsafe(24)
        st.session_state["_mailqr_visitor_id"] = visitor_id

    with connect_db() as conn:
        conn.execute(
            "INSERT INTO link_opens(visitor_id) VALUES (?)",
            (visitor_id,),
        )

    st.session_state["_mailqr_counted_this_session"] = True


init_db()


# -----------------------------
# Read email details from URL
# -----------------------------
def query_value(key):
    value = st.query_params.get(key, "")
    return value if isinstance(value, str) else ""


incoming = {key: query_value(key) for key in TRACKED_KEYS}
is_shared_link = any(value.strip() for value in incoming.values())

if is_shared_link:
    record_open_once_per_session()


# -----------------------------
# Page title and analytics
# -----------------------------
st.title("📧 MailQR")
st.caption("Create a QR code and share a prefilled email link.")

st.subheader("📊 Link Analytics")
total_opens, unique_visitors = get_stats()

col1, col2 = st.columns(2)
col1.metric("Total Link Opens", total_opens)
col2.metric("Unique Browser Sessions", unique_visitors)

st.caption(
    "Counts share-link visits, not emails sent. Unique visitors are estimated "
    "using a temporary Streamlit session; a new session or browser may count "
    "the same person again. No IP addresses are stored."
)

if is_shared_link:
    st.success("Share link opened. This visit has been counted for this session.")


# -----------------------------
# Email form
# -----------------------------
st.subheader("✉️ Compose Email")

with st.form("mailqr_form"):
    to = st.text_input("To", value=incoming["to"], placeholder="person@example.com")
    cc = st.text_input("CC", value=incoming["cc"])
    bcc = st.text_input("BCC", value=incoming["bcc"])
    subject = st.text_input("Subject", value=incoming["subject"])
    body = st.text_area("Message", value=incoming["body"], height=160)

    submitted = st.form_submit_button("Generate QR & Link", type="primary")


def make_share_url(values):
    base_url = APP_URL.rstrip("/")
    if not base_url:
        # Useful for local testing only; other devices cannot use localhost.
        base_url = "http://localhost:8501"
    query = urlencode({k: v for k, v in values.items() if v.strip()})
    return f"{base_url}/?{query}" if query else base_url


if submitted:
    values = {
        "to": to.strip(),
        "cc": cc.strip(),
        "bcc": bcc.strip(),
        "subject": subject.strip(),
        "body": body.strip(),
    }

    share_url = make_share_url(values)
    st.session_state["mailqr_share_url"] = share_url
    st.session_state["mailqr_email_values"] = values

share_url = st.session_state.get("mailqr_share_url", "")
saved_values = st.session_state.get("mailqr_email_values", {})

if share_url:
    st.subheader("🔗 Your Share Link")
    st.code(share_url, language=None)
    st.link_button("Open Share Link", share_url)

    qr = qrcode.QRCode(box_size=8, border=3)
    qr.add_data(share_url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")

    st.subheader("📱 Your QR Code")
    st.image(qr_image, caption="Scan to open the MailQR share link", width=260)

    st.download_button(
        "Download QR Code",
        data=_qr_bytes(qr_image) if False else b"",
        file_name="mailqr.png",
        mime="image/png",
        disabled=True,
        help="Use the QR download code below to enable image downloads.",
    )

    email_values = saved_values
    gmail_params = {
        "view": "cm",
        "fs": "1",
        "to": email_values.get("to", ""),
        "cc": email_values.get("cc", ""),
        "bcc": email_values.get("bcc", ""),
        "su": email_values.get("subject", ""),
        "body": email_values.get("body", ""),
    }
    gmail_url = "https://mail.google.com/mail/?" + urlencode(
        {k: v for k, v in gmail_params.items() if v}
    )

    st.link_button("Open Gmail with Email Details", gmail_url)

    st.info(
        "Share the QR/link to count visits. Gmail opens separately with the "
        "email details prefilled. The app cannot verify whether an email was sent."
    )
