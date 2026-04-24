"""
Google Sheets CRM tool — read/write the lead tracking spreadsheet.
Falls back to local SQLite when Sheets is not configured.
"""
import os
import json
from typing import Optional
from utils.helpers import get_logger

log = get_logger(__name__)

HEADERS = [
    "ID", "Company", "Website", "Contact Name", "Contact Role", "Email",
    "Market", "Customer Type", "Source", "ICP Score", "Score Reason",
    "Hot Signals", "Tech Stack", "Hook", "Email Subject", "Email Body",
    "Email Sent", "Email Sent At", "Reply Status",
    "Follow-up 2 Due", "Follow-up 3 Due", "Status", "Notes", "Revenue",
]


def _get_gspread_client():
    from google.oauth2.service_account import Credentials
    import gspread

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_file and os.path.isfile(creds_file):
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    else:
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT")
        if not creds_json:
            raise ValueError("No Google service account credentials found")
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)

    return gspread.authorize(creds)


def _get_sheet(tab_name: str = "Leads"):
    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        return None
    try:
        gc = _get_gspread_client()
        wb = gc.open_by_key(sheet_id)
        try:
            return wb.worksheet(tab_name)
        except Exception:
            ws = wb.add_worksheet(title=tab_name, rows=1000, cols=len(HEADERS))
            ws.append_row(HEADERS)
            return ws
    except Exception as e:
        log.warning(f"Google Sheets unavailable: {e}")
        return None


def _lead_to_row(lead: dict) -> list:
    contact = lead.get("contact") or {}
    return [
        lead.get("id", ""),
        lead.get("company_name", ""),
        lead.get("website", ""),
        contact.get("name", "") or lead.get("founder_name", ""),
        contact.get("role", ""),
        contact.get("email", ""),
        lead.get("market", ""),
        lead.get("customer_type", ""),
        lead.get("source", ""),
        lead.get("icp_score", ""),
        lead.get("score_reason", ""),
        ", ".join(lead.get("hot_signals") or []),
        ", ".join(lead.get("tech_stack") or []),
        lead.get("hook", ""),
        lead.get("email_subject", ""),
        lead.get("email_body", ""),
        "Yes" if lead.get("email_sent") else "No",
        lead.get("email_sent_at", ""),
        lead.get("status", "pending"),
        "",  # Follow-up 2 Due
        "",  # Follow-up 3 Due
        lead.get("status", ""),
        "",  # Notes
        "",  # Revenue
    ]


def log_lead_to_sheets(lead: dict) -> Optional[str]:
    """Append a lead row to Google Sheets. Returns row number or None."""
    ws = _get_sheet("Leads")
    if ws is None:
        # Fallback to local DB
        from utils.local_db import upsert_lead
        upsert_lead(lead)
        return None

    try:
        row = _lead_to_row(lead)
        ws.append_row(row, value_input_option="USER_ENTERED")
        all_rows = ws.get_all_values()
        row_id = str(len(all_rows))
        log.info(f"Lead logged to Sheets row {row_id}: {lead.get('company_name')}")
        return row_id
    except Exception as e:
        log.error(f"Sheets log error: {e}")
        from utils.local_db import upsert_lead
        upsert_lead(lead)
        return None


def update_lead_status(row_id: str, status: str, reply_status: str = "") -> bool:
    ws = _get_sheet("Leads")
    if ws is None:
        return False
    try:
        row = int(row_id)
        status_col = HEADERS.index("Status") + 1
        ws.update_cell(row, status_col, status)
        if reply_status:
            reply_col = HEADERS.index("Reply Status") + 1
            ws.update_cell(row, reply_col, reply_status)
        return True
    except Exception as e:
        log.error(f"Sheets update error: {e}")
        return False


def log_follow_up_queue(lead: dict, touch: int, send_date: str) -> None:
    ws = _get_sheet("Sequences")
    if ws is None:
        from utils.local_db import schedule_follow_up
        schedule_follow_up(lead.get("id", ""), touch, send_date)
        return

    try:
        if ws.row_count == 1:
            ws.append_row(["Lead ID", "Company", "Email", "Touch", "Send Date", "Status"])
        ws.append_row([
            lead.get("id", ""),
            lead.get("company_name", ""),
            (lead.get("contact") or {}).get("email", ""),
            touch,
            send_date,
            "pending",
        ])
    except Exception as e:
        log.error(f"Sheets follow-up queue error: {e}")
