"""
SQLite-backed local CRM — used when Google Sheets is not configured.
Stores leads, follow-up queue, and pipeline run logs.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leads.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS leads (
                id              TEXT PRIMARY KEY,
                company_name    TEXT,
                website         TEXT,
                contact_name    TEXT,
                contact_email   TEXT,
                contact_role    TEXT,
                location        TEXT,
                market          TEXT,
                customer_type   TEXT,
                source          TEXT,
                source_url      TEXT,
                icp_score       INTEGER,
                score_reason    TEXT,
                hot_signals     TEXT,
                tech_stack      TEXT,
                hook            TEXT,
                email_subject   TEXT,
                email_body      TEXT,
                email_sent      INTEGER DEFAULT 0,
                email_sent_at   TEXT,
                reply_status    TEXT DEFAULT 'no_reply',
                follow_up_2_due TEXT,
                follow_up_3_due TEXT,
                status          TEXT DEFAULT 'pending',
                created_at      TEXT,
                updated_at      TEXT,
                notes           TEXT
            );

            CREATE TABLE IF NOT EXISTS follow_up_queue (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id     TEXT,
                touch       INTEGER,
                send_date   TEXT,
                status      TEXT DEFAULT 'pending',
                sent_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date        TEXT,
                leads_found     INTEGER,
                leads_qualified INTEGER,
                emails_sent     INTEGER,
                errors          TEXT,
                duration_secs   REAL
            );
        """)


def upsert_lead(lead: dict) -> None:
    now = datetime.utcnow().isoformat()
    with _conn() as con:
        existing = con.execute("SELECT id FROM leads WHERE id=?", (lead["id"],)).fetchone()
        if existing:
            con.execute(
                "UPDATE leads SET updated_at=?, status=?, email_sent=?, email_sent_at=?,"
                " reply_status=? WHERE id=?",
                (now, lead.get("status", "pending"),
                 1 if lead.get("email_sent") else 0,
                 lead.get("email_sent_at"),
                 lead.get("reply_status", "no_reply"),
                 lead["id"]),
            )
        else:
            import json
            con.execute(
                """INSERT INTO leads
                   (id,company_name,website,contact_name,contact_email,contact_role,
                    location,market,customer_type,source,source_url,icp_score,score_reason,
                    hot_signals,tech_stack,hook,email_subject,email_body,
                    email_sent,email_sent_at,status,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (lead.get("id"), lead.get("company_name"), lead.get("website"),
                 lead.get("contact", {}).get("name") if lead.get("contact") else None,
                 lead.get("contact", {}).get("email") if lead.get("contact") else None,
                 lead.get("contact", {}).get("role") if lead.get("contact") else None,
                 lead.get("location"), lead.get("market"), lead.get("customer_type"),
                 lead.get("source"), lead.get("source_url"),
                 lead.get("icp_score"), lead.get("score_reason"),
                 json.dumps(lead.get("hot_signals", [])),
                 json.dumps(lead.get("tech_stack", [])),
                 lead.get("hook"),
                 lead.get("email_subject"), lead.get("email_body"),
                 1 if lead.get("email_sent") else 0,
                 lead.get("email_sent_at"),
                 lead.get("status", "pending"),
                 now, now),
            )


def schedule_follow_up(lead_id: str, touch: int, send_date: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO follow_up_queue (lead_id, touch, send_date) VALUES (?,?,?)",
            (lead_id, touch, send_date),
        )


def get_due_follow_ups(today: Optional[str] = None) -> list[dict]:
    today = today or datetime.utcnow().date().isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM follow_up_queue WHERE status='pending' AND send_date<=?",
            (today,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_follow_up_sent(queue_id: int) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE follow_up_queue SET status='sent', sent_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), queue_id),
        )


def log_pipeline_run(run: dict) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO pipeline_runs (run_date,leads_found,leads_qualified,"
            "emails_sent,errors,duration_secs) VALUES (?,?,?,?,?,?)",
            (run.get("run_date"), run.get("leads_found", 0),
             run.get("leads_qualified", 0), run.get("emails_sent", 0),
             str(run.get("errors", [])), run.get("duration_secs", 0)),
        )
