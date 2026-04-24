"""
Gmail API tool — send emails and poll for replies.
Uses OAuth2 (free). Falls back to SMTP with App Password if API not configured.
"""
import os
import base64
import json
from email.mime.text import MIMEText
from typing import Optional
from utils.helpers import get_logger

log = get_logger(__name__)


def _get_gmail_service():
    """Build authenticated Gmail API service."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        client_id=os.getenv("GMAIL_CLIENT_ID"),
        client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _build_message(to: str, subject: str, body: str,
                   sender: str, reply_to: str = "") -> dict:
    msg = MIMEText(body, "plain")
    msg["To"] = to
    msg["From"] = sender
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def send_email_gmail_api(to: str, subject: str, body: str) -> bool:
    """Send an email via Gmail API. Returns True on success."""
    sender = os.getenv("YOUR_EMAIL", "")
    if not all([
        os.getenv("GMAIL_CLIENT_ID"),
        os.getenv("GMAIL_CLIENT_SECRET"),
        os.getenv("GMAIL_REFRESH_TOKEN"),
    ]):
        log.warning("Gmail API not configured — saving email to draft file instead")
        return _save_draft(to, subject, body)

    try:
        service = _get_gmail_service()
        message = _build_message(to, subject, body, sender)
        service.users().messages().send(userId="me", body=message).execute()
        log.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        log.error(f"Gmail API send error: {e}")
        return False


def send_email_smtp(to: str, subject: str, body: str) -> bool:
    """
    Send via SMTP using Gmail App Password (alternative to OAuth2).
    Set GMAIL_APP_PASSWORD in .env (not your regular password).
    Generate: Google Account → Security → App Passwords.
    """
    import smtplib
    sender = os.getenv("YOUR_EMAIL", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not (sender and password):
        return _save_draft(to, subject, body)
    try:
        msg = MIMEText(body, "plain")
        msg["To"] = to
        msg["From"] = sender
        msg["Subject"] = subject
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.sendmail(sender, to, msg.as_string())
        log.info(f"Email sent via SMTP to {to}")
        return True
    except Exception as e:
        log.error(f"SMTP send error: {e}")
        return _save_draft(to, subject, body)


def send_email(to: str, subject: str, body: str) -> bool:
    """
    Smart send — tries Gmail API first, then SMTP App Password, then saves draft.
    """
    if os.getenv("GMAIL_REFRESH_TOKEN"):
        return send_email_gmail_api(to, subject, body)
    if os.getenv("GMAIL_APP_PASSWORD"):
        return send_email_smtp(to, subject, body)
    return _save_draft(to, subject, body)


def _save_draft(to: str, subject: str, body: str) -> bool:
    """Save email to a drafts file when no sending method is configured."""
    import os
    from datetime import datetime
    drafts_path = os.path.join(os.path.dirname(__file__), "..", "data", "email_drafts.jsonl")
    os.makedirs(os.path.dirname(drafts_path), exist_ok=True)
    with open(drafts_path, "a", encoding="utf-8") as f:
        record = {
            "to": to, "subject": subject, "body": body,
            "saved_at": datetime.utcnow().isoformat(),
        }
        f.write(json.dumps(record) + "\n")
    log.info(f"Email draft saved (no send method configured): {to} — {subject}")
    return True  # Don't block pipeline; user reviews drafts manually


def check_replies(since_days: int = 2) -> list[dict]:
    """
    Poll Gmail inbox for replies to our outreach emails.
    Returns list of {thread_id, from, subject, snippet}.
    """
    if not os.getenv("GMAIL_REFRESH_TOKEN"):
        return []
    try:
        service = _get_gmail_service()
        from datetime import datetime, timedelta
        since = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y/%m/%d")
        query = f"in:inbox after:{since} -from:me"
        result = service.users().messages().list(
            userId="me", q=query, maxResults=50
        ).execute()

        replies = []
        for msg_ref in result.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "In-Reply-To"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            if headers.get("In-Reply-To"):
                replies.append({
                    "thread_id": msg.get("threadId"),
                    "message_id": msg_ref["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "snippet": msg.get("snippet", ""),
                })
        return replies
    except Exception as e:
        log.error(f"Gmail check_replies error: {e}")
        return []
