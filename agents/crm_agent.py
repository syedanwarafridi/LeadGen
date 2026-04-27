"""
Node 6 — CRM Agent
Logs every processed lead to Google Sheets (free) or local SQLite (fallback).
Also logs the pipeline run stats.
"""
from datetime import datetime
from utils.helpers import get_logger
from graph.state import PipelineState

log = get_logger(__name__)


def run_crm(state: PipelineState) -> PipelineState:
    """LangGraph Node 6 — log all processed leads to CRM."""
    log.info("=== Node 6: CRM ===")
    qualified = state.get("qualified", [])
    errors = list(state.get("errors", []))

    from tools.sheets_tool import log_lead_to_sheets

    processed = []
    for lead in qualified:
        try:
            row_id = log_lead_to_sheets(lead)
            updated = {**lead, "crm_row_id": row_id}
            processed.append(updated)

            # Mark as seen so future runs skip this company
            from utils.local_db import mark_lead_seen
            from utils.helpers import extract_domain
            mark_lead_seen(
                extract_domain(lead.get("website") or "") or "",
                lead.get("company_name") or "",
            )

            log.info(
                f"  Logged: {lead.get('company_name')} | "
                f"score={lead.get('icp_score')} | "
                f"status={lead.get('status')} | "
                f"row={row_id}"
            )
        except Exception as e:
            log.error(f"CRM log error for {lead.get('company_name')}: {e}")
            errors.append(f"crm:{lead.get('company_name')}:{e}")
            processed.append(lead)

    # Log the full pipeline run summary
    _log_run_summary(state, processed, errors)

    log.info(f"CRM complete: {len(processed)} leads logged")
    return {**state, "qualified": processed, "processed": processed, "errors": errors}


def _log_run_summary(state: PipelineState, processed: list, errors: list) -> None:
    """Log pipeline run stats to local DB and print a summary."""
    from utils.local_db import log_pipeline_run, init_db
    init_db()

    sent = sum(1 for l in processed if l.get("email_sent"))
    qualified_count = len(processed)
    raw_count = len(state.get("leads", []))

    run = {
        "run_date": state.get("run_date", datetime.utcnow().isoformat()),
        "leads_found": raw_count,
        "leads_qualified": qualified_count,
        "emails_sent": sent,
        "errors": errors,
        "duration_secs": 0,
    }
    try:
        log_pipeline_run(run)
    except Exception as e:
        log.debug(f"Run summary log error: {e}")

    log.info(
        f"\n{'='*50}\n"
        f"  PIPELINE RUN COMPLETE\n"
        f"  Date:       {run['run_date'][:10]}\n"
        f"  Discovered: {raw_count} leads\n"
        f"  Qualified:  {qualified_count} leads (≥{7} ICP score)\n"
        f"  Emails sent:{sent}\n"
        f"  Errors:     {len(errors)}\n"
        f"{'='*50}"
    )
