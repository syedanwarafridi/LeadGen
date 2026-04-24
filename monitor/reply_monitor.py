"""
Reply Monitor — polls Gmail inbox every 2 hours for replies to our outreach emails.
When a reply is detected, it updates the lead status in the CRM to 'Replied'
and stops the follow-up sequence for that lead.

Run as a background process:
  python monitor/reply_monitor.py

Or integrate into a scheduler (runs after each pipeline run).
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.helpers import get_logger
from utils.local_db import init_db, _conn

log = get_logger("reply_monitor")

CHECK_INTERVAL_SECS = 60 * 120  # 2 hours


def _extract_email_address(from_header: str) -> str:
    """Extract plain email from 'Name <email@domain.com>' format."""
    import re
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1).lower().strip()
    return from_header.lower().strip()


def check_and_update_replies() -> int:
    """
    Poll Gmail for replies, cross-reference with our leads DB,
    and update status. Returns number of replies found.
    """
    if not os.getenv("GMAIL_REFRESH_TOKEN"):
        log.debug("Gmail not configured — skipping reply check")
        return 0

    from tools.gmail_tool import check_replies
    replies = check_replies(since_days=14)

    if not replies:
        log.info("No new replies detected")
        return 0

    log.info(f"Found {len(replies)} potential replies — checking against leads DB")
    init_db()
    matched = 0

    for reply in replies:
        sender_email = _extract_email_address(reply.get("from", ""))
        if not sender_email:
            continue

        with _conn() as con:
            row = con.execute(
                "SELECT id, company_name, status FROM leads WHERE LOWER(contact_email)=?",
                (sender_email,),
            ).fetchone()

        if row:
            lead_id = row["id"]
            company = row["company_name"]
            old_status = row["status"]

            if old_status not in ("replied", "booked"):
                _mark_replied(lead_id, reply)
                _cancel_pending_follow_ups(lead_id)
                log.info(f"  ✓ Reply from {sender_email} ({company}) — marked as Replied")
                matched += 1

    log.info(f"Reply check complete: {matched} lead(s) updated")
    return matched


def _mark_replied(lead_id: str, reply_data: dict) -> None:
    from datetime import datetime
    with _conn() as con:
        con.execute(
            "UPDATE leads SET reply_status='replied', status='replied', updated_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), lead_id),
        )

    # Also update Google Sheets if configured
    try:
        with _conn() as con:
            row = con.execute("SELECT crm_row_id FROM leads WHERE id=?", (lead_id,)).fetchone()
        if row and row["crm_row_id"]:
            from tools.sheets_tool import update_lead_status
            update_lead_status(row["crm_row_id"], "replied", reply_status="Replied")
    except Exception as e:
        log.debug(f"Sheets update failed for {lead_id}: {e}")


def _cancel_pending_follow_ups(lead_id: str) -> None:
    """Mark all pending follow-ups for this lead as cancelled."""
    with _conn() as con:
        con.execute(
            "UPDATE follow_up_queue SET status='cancelled' WHERE lead_id=? AND status='pending'",
            (lead_id,),
        )
    log.debug(f"Cancelled follow-ups for {lead_id}")


def run_monitor_loop() -> None:
    """Run the reply monitor in a continuous loop."""
    log.info(f"Reply monitor started — checking every {CHECK_INTERVAL_SECS // 60} minutes")
    while True:
        try:
            check_and_update_replies()
        except Exception as e:
            log.error(f"Monitor loop error: {e}")
        time.sleep(CHECK_INTERVAL_SECS)


if __name__ == "__main__":
    run_monitor_loop()
