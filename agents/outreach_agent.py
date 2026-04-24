"""
Node 5 — Outreach Agent
Sends Email 1 via Gmail API (free) and schedules follow-up touches.
Hard-capped at MAX_EMAILS_PER_DAY to protect sender reputation.

Touch sequence:
  Email 1 — Day 0  (this node)
  Email 2 — Day 4  (follow-up queue)
  Email 3 — Day 9  (final note)

If Gmail is not configured, drafts are saved to data/email_drafts.jsonl
for manual review and sending.
"""
import os
from datetime import datetime, timedelta
from utils.helpers import get_logger
from graph.state import PipelineState

log = get_logger(__name__)


def _days_later(n: int) -> str:
    return (datetime.utcnow() + timedelta(days=n)).date().isoformat()


def run_outreach(state: PipelineState) -> PipelineState:
    """LangGraph Node 5 — send Email 1 and queue follow-ups."""
    log.info("=== Node 5: Outreach ===")
    qualified = state.get("qualified", [])
    errors = list(state.get("errors", []))

    max_per_day = int(os.getenv("MAX_EMAILS_PER_DAY", "20"))
    sent_count = 0
    processed = []

    for lead in qualified:
        contact = lead.get("contact") or {}
        to_email = contact.get("email") or ""

        # Skip leads without a valid email address
        if not to_email or "@" not in to_email:
            log.info(f"  Skip (no email): {lead.get('company_name')}")
            processed.append({**lead, "status": "skip", "email_sent": False})
            continue

        if sent_count >= max_per_day:
            log.info(f"  Daily cap reached ({max_per_day}). Remaining leads queued for tomorrow.")
            processed.append({**lead, "status": "queued"})
            continue

        subject = lead.get("email_subject", "")
        body = lead.get("email_body", "")

        if not subject or not body:
            log.warning(f"  Skip (no email drafted): {lead.get('company_name')}")
            processed.append({**lead, "status": "skip", "email_sent": False})
            continue

        # Send Email 1
        from tools.gmail_tool import send_email
        success = send_email(to_email, subject, body)

        if success:
            sent_count += 1
            sent_at = datetime.utcnow().isoformat()
            log.info(f"  ✓ Sent to {to_email}: {subject[:60]}")

            # Schedule follow-up touches
            from tools.sheets_tool import log_follow_up_queue
            log_follow_up_queue(lead, touch=2, send_date=_days_later(4))
            log_follow_up_queue(lead, touch=3, send_date=_days_later(9))

            processed.append({
                **lead,
                "email_sent": True,
                "email_sent_at": sent_at,
                "status": "sent",
            })
        else:
            log.warning(f"  ✗ Send failed: {lead.get('company_name')}")
            errors.append(f"outreach:send_failed:{lead.get('company_name')}")
            processed.append({**lead, "status": "error", "email_sent": False})

    log.info(f"Outreach complete: {sent_count} sent, {len(processed) - sent_count} skipped/queued")
    return {**state, "qualified": processed, "errors": errors}
