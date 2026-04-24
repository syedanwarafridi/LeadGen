"""
Pipeline entry point.

Usage:
  # Run full automated pipeline (discovery → send emails)
  python scheduler/run_pipeline.py

  # Phase 1 MVP: score a single lead from manual input
  python scheduler/run_pipeline.py --manual

  # Dry run: run pipeline but skip sending emails
  python scheduler/run_pipeline.py --dry-run

  # Run as daily scheduler (runs at 8 AM UTC every day)
  python scheduler/run_pipeline.py --schedule
"""
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.helpers import get_logger
from utils.local_db import init_db

log = get_logger("pipeline")


def run_full_pipeline(dry_run: bool = False) -> dict:
    """Run the complete 6-node LangGraph pipeline."""
    from graph.pipeline import get_pipeline

    if dry_run:
        os.environ["MAX_EMAILS_PER_DAY"] = "0"
        log.info("DRY RUN mode — no emails will be sent")

    init_db()
    pipeline = get_pipeline()

    initial_state = {
        "leads": [],
        "qualified": [],
        "processed": [],
        "run_date": datetime.utcnow().isoformat(),
        "errors": [],
    }

    start = time.time()
    log.info(f"Pipeline started at {initial_state['run_date']}")

    final_state = pipeline.invoke(initial_state)
    elapsed = time.time() - start

    log.info(f"Pipeline finished in {elapsed:.1f}s")
    return final_state


def run_manual_mode() -> None:
    """
    Phase 1 MVP — score + write email from manual text input.
    No discovery APIs needed. Just paste company info and get a scored lead + draft email.
    """
    from dotenv import load_dotenv
    load_dotenv()

    from agents.scoring_agent import score_lead
    from agents.personalization_agent import write_email
    from utils.llm import get_llm
    from utils.helpers import make_id

    print("\n" + "="*60)
    print("  LEAD GENERATION — Manual Mode (Phase 1 MVP)")
    print("="*60)
    print("Paste any company/founder info (press Enter twice when done):\n")

    lines = []
    try:
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
    except EOFError:
        pass

    raw_input = "\n".join(lines).strip()
    if not raw_input:
        print("No input provided.")
        return

    llm = get_llm(temperature=0.0)

    # Build a minimal lead dict from the raw text
    lead = {
        "id": make_id(),
        "company_name": "Manual Lead",
        "website": "",
        "linkedin_url": "",
        "location": "Unknown",
        "market": "Unknown",
        "team_size": 0,
        "funding": None,
        "source": "manual",
        "source_url": "",
        "raw_signals": [],
        "description": raw_input[:500],
        "founder_name": None,
        "founder_handle": None,
    }

    print("\n[Scoring lead...]")
    scored = score_lead(lead, llm)

    score = scored.get("icp_score", 0)
    reason = scored.get("score_reason", "")
    print(f"\n{'='*60}")
    print(f"  ICP Score:    {score}/10")
    print(f"  Reason:       {reason}")
    print(f"  Customer type:{scored.get('customer_type', 'unknown')}")
    print(f"  Hot signals:  {', '.join(scored.get('hot_signals') or [])}")

    min_score = int(os.getenv("MIN_ICP_SCORE", "7"))
    if score < min_score:
        print(f"\n  [SKIP] Score {score} < {min_score} — not qualified")
        print(f"  Reason: {scored.get('skip_reason', 'below threshold')}")
        print("="*60)
        return

    print(f"\n[Writing personalized email...]")
    # Add minimal contact for personalization
    scored["contact"] = {"name": "", "role": "Founder", "email": ""}
    scored["hook"] = raw_input[:150]
    emailed = write_email(scored, get_llm(temperature=0.7))

    print(f"\n{'='*60}")
    print(f"  Subject: {emailed.get('email_subject', '')}")
    print(f"\n  Body:\n{emailed.get('email_body', '')}")
    print("="*60)

    # Ask to save
    save = input("\nSave this to local DB? (y/n): ").strip().lower()
    if save == "y":
        from utils.local_db import upsert_lead, init_db
        init_db()
        upsert_lead(emailed)
        print("Saved to data/leads.db")


def run_follow_ups() -> None:
    """Check and send any due follow-up emails from the queue."""
    from utils.local_db import get_due_follow_ups, mark_follow_up_sent, init_db
    init_db()

    due = get_due_follow_ups()
    if not due:
        log.info("No follow-ups due today")
        return

    log.info(f"Processing {len(due)} follow-up(s)")

    from utils.local_db import _conn
    from tools.gmail_tool import send_email
    from utils.llm import get_llm
    from prompts.personalization_prompt import FOLLOW_UP_2_PROMPT, FOLLOW_UP_3_PROMPT
    from agents.personalization_agent import _parse_email_json
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = get_llm(temperature=0.5)

    for item in due:
        lead_id = item["lead_id"]
        touch = item["touch"]
        queue_id = item["id"]

        # Fetch lead from DB
        with _conn() as con:
            row = con.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            continue

        row = dict(row)
        to_email = row.get("contact_email") or ""
        if not to_email:
            mark_follow_up_sent(queue_id)
            continue

        prompt_text = FOLLOW_UP_2_PROMPT if touch == 2 else FOLLOW_UP_3_PROMPT
        context = (
            f"Original subject: {row.get('email_subject', '')}\n"
            f"Company: {row.get('company_name', '')}\n"
            f"Contact: {row.get('contact_name', '')}\n"
            f"Your name: {os.getenv('YOUR_NAME', '')}\n"
            f"Touch number: {touch}"
        )

        chain = (
            ChatPromptTemplate.from_messages([("system", prompt_text), ("human", "{ctx}")])
            | llm | StrOutputParser()
        )
        raw = chain.invoke({"ctx": context})
        result = _parse_email_json(raw)

        subject = result.get("subject") or f"Re: {row.get('email_subject', '')}"
        body = result.get("body") or ""

        if body:
            send_email(to_email, subject, body)
            mark_follow_up_sent(queue_id)
            log.info(f"Follow-up touch {touch} sent to {to_email}")


def run_scheduled() -> None:
    """Run pipeline on a daily schedule."""
    import schedule

    send_hour = int(os.getenv("SEND_HOUR_UTC", "8"))

    def morning_run():
        log.info("Scheduled morning run starting...")
        run_full_pipeline()

    def afternoon_followups():
        log.info("Scheduled follow-up check starting...")
        run_follow_ups()

    schedule.every().day.at(f"{send_hour:02d}:00").do(morning_run)
    schedule.every().day.at("14:00").do(afternoon_followups)

    log.info(f"Scheduler active — pipeline runs daily at {send_hour:02d}:00 UTC")
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Lead Generation Pipeline")
    parser.add_argument("--manual",   action="store_true", help="Phase 1: manual lead input mode")
    parser.add_argument("--dry-run",  action="store_true", help="Run pipeline without sending emails")
    parser.add_argument("--schedule", action="store_true", help="Run as daily scheduled job")
    parser.add_argument("--followups", action="store_true", help="Send due follow-up emails only")
    args = parser.parse_args()

    if args.manual:
        run_manual_mode()
    elif args.schedule:
        run_scheduled()
    elif args.followups:
        run_follow_ups()
    else:
        run_full_pipeline(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
