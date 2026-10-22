
import os
import sqlite3
import secrets
from pathlib import Path
from io import BytesIO
from urllib.parse import urlencode

import qrcode
import streamlit as st


# ==========================================
# MAILQR - STREAMLIT APP
# ==========================================

st.set_page_config(
    page_title="MailQR",
    page_icon="📧",
    layout="centered",
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(
    os.environ.get(
        "MAILQR_DB_PATH",
        str(BASE_DIR / "mailqr_stats.sqlite3")
    )
)

TRACKED_KEYS = ("to", "cc", "bcc", "subject", "body")


def get_app_url():
    """Get the public app URL from environment or Streamlit secrets."""
    url = os.environ.get("APP_URL", "")

    try:
        url = st.secrets.get("APP_URL", url)
    except Exception:
        pass

    return str(url).strip().rstrip("/")


def connect_db():
    return sqlite3.connect(DB_PATH, timeout=15)


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS link_opens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT NOT NULL,
                link_id TEXT NOT NULL,
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


def get_query_value(key):
    value = st.query_params.get(key, "")
    return value if isinstance(value, str) else ""


def get_incoming_email():
    return {
        key: get_query_value(key)
        for key in TRACKED_KEYS
    }


def record_share_open(link_id):
    """
    Count a shared-link visit once per browser session per link.
    Streamlit sessions are approximate visitors, not verified identities.
    """
    session_key = f"_mailqr_counted_{link_id}"

    if st.session_state.get(session_key):
        return

    if "_mailqr_visitor_id" not in st.session_state:
        st.session_state["_mailqr_visitor_id"] = secrets.token_urlsafe(24)

    visitor_id = st.session_state["_mailqr_visitor_id"]

    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO link_opens (visitor_id, link_id)
            VALUES (?, ?)
            """,
            (visitor_id, link_id),
        )

    st.session_state[session_key] = True


def make_share_url(values):
    app_url = get_app_url()

    if not app_url:
        return None

    query = urlencode({
        key: value
        for key, value in values.items()
        if value.strip()
    })

    if not query:
        return app_url

    return f"{app_url}/?{query}"


def make_qr_png(url):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=9,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def make_gmail_url(values):
    gmail_fields = {
        "view": "cm",
        "fs": "1",
        "to": values.get("to", ""),
        "cc": values.get("cc", ""),
        "bcc": values.get("bcc", ""),
        "su": values.get("subject", ""),
        "body": values.get("body", ""),
    }

    query = urlencode({
        key: value
        for key, value in gmail_fields.items()
        if value
    })

    return "https://mail.google.com/mail/?" + query


# ==========================================
# INITIALIZE DATABASE
# ==========================================

init_db()

incoming = get_incoming_email()
is_shared_link = any(
    value.strip() for value in incoming.values()
)

if is_shared_link:
    # Identify this particular share link without storing email contents.
    link_id = secrets.token_hex(16)
    link_id = st.query_params.get("_mailqr_link_id", "")

    if not link_id:
        # Stable identifier derived from the URL fields for counting.
        import hashlib
        canonical = urlencode(sorted(incoming.items()))
        link_id = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()[:32]

    record_share_open(link_id)


# ==========================================
# PAGE HEADER
# ==========================================

st.title("📧 MailQR")
st.write(
    "Generate a QR code and a shareable link "
    "to open a prefilled email in Gmail."
)

st.caption(
    "This app prepares email details. It does not send emails."
)


# ==========================================
# ANALYTICS DASHBOARD
# ==========================================

st.subheader("📊 Link Analytics")

total_opens, unique_visitors = get_stats()

metric1, metric2 = st.columns(2)

metric1.metric(
    label="Total Link Opens",
    value=total_opens,
)

metric2.metric(
    label="Unique Browser Sessions",
    value=unique_visitors,
)

st.caption(
    "Counts share-link visits, not emails sent. "
    "Unique visitors are estimated from Streamlit sessions; "
    "the same person may be counted again in a new session or browser. "
    "IP addresses are not stored."
)


# ==========================================
# EMAIL FORM
# ==========================================

st.subheader("✉️ Compose Email")

with st.form("mailqr_form"):
    to = st.text_input(
        "To",
        value=incoming["to"],
        placeholder="person@example.com",
    )

    cc = st.text_input(
        "CC",
        value=incoming["cc"],
    )

    bcc = st.text_input(
        "BCC",
        value=incoming["bcc"],
    )

    subject = st.text_input(
        "Subject",
        value=incoming["subject"],
    )

    body = st.text_area(
        "Email Message",
        value=incoming["body"],
        height=180,
    )

    submitted = st.form_submit_button(
        "Generate QR Code & Link",
        type="primary",
        use_container_width=True,
    )


# ==========================================
# GENERATE SHARE LINK AND QR
# ==========================================

if submitted:
    values = {
        "to": to.strip(),
        "cc": cc.strip(),
        "bcc": bcc.strip(),
        "subject": subject.strip(),
        "body": body.strip(),
    }

    if not any(values.values()):
        st.warning("Please enter at least one email field.")
    else:
        st.session_state["mailqr_values"] = values

values = st.session_state.get("mailqr_values")

if values:
    st.divider()
    st.subheader("🔗 Share Link")

    share_url = make_share_url(values)

    if share_url:
        st.code(share_url, language=None)

        st.link_button(
            "Open Share Link",
            share_url,
            use_container_width=True,
        )

        st.subheader("📱 QR Code")

        qr_png = make_qr_png(share_url)

        st.image(
            qr_png,
            caption="Scan to open the shared MailQR link",
            width=280,
        )

        st.download_button(
            "⬇️ Download QR Code",
            data=qr_png,
            file_name="mailqr.png",
            mime="image/png",
            use_container_width=True,
        )

        st.subheader("✉️ Open Gmail")

        gmail_url = make_gmail_url(values)

        st.link_button(
            "Open Gmail with Email Details",
            gmail_url,
            use_container_width=True,
        )

        st.info(
            "The share link opens this MailQR app with the email fields "
            "prefilled. The Gmail button opens Gmail with those details. "
            "The app cannot verify whether an email was actually sent."
        )

    else:
        st.error(
            "Your public app URL is not configured. "
            "Set APP_URL to your deployed Streamlit URL, then restart "
            "the app. For example: "
            "https://your-app-name.streamlit.app"
        )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "MailQR · Link analytics count visits only. "
    "No email is sent automatically."
)
