"""
LangGraph state definitions.
LeadState — one lead moving through the pipeline.
PipelineState — the full daily run, containing all leads.
"""
from typing import TypedDict, List, Optional, Dict, Any


class LeadState(TypedDict):
    # ── Discovery (Node 1) ───────────────────────────────────
    id:             str
    company_name:   str
    website:        str
    linkedin_url:   str
    location:       str
    market:         str           # US | UK | UAE | Unknown
    team_size:      int
    funding:        Optional[Dict[str, Any]]
    source:         str           # reddit | hackernews | producthunt | github | indiehackers
    source_url:     str
    raw_signals:    List[str]
    description:    str
    founder_name:   Optional[str]
    founder_handle: Optional[str]

    # ── Scoring (Node 2) ─────────────────────────────────────
    icp_score:      Optional[int]
    score_reason:   Optional[str]
    hot_signals:    Optional[List[str]]
    customer_type:  Optional[str]  # startup | smb | individual
    skip_reason:    Optional[str]

    # ── Enrichment (Node 3) ──────────────────────────────────
    contact:        Optional[Dict[str, Any]]  # name, role, email, linkedin, recent_post
    tech_stack:     Optional[List[str]]
    hook:           Optional[str]

    # ── Personalization (Node 4) ─────────────────────────────
    email_subject:  Optional[str]
    email_body:     Optional[str]

    # ── Outreach (Node 5) ────────────────────────────────────
    email_sent:     Optional[bool]
    email_sent_at:  Optional[str]

    # ── CRM (Node 6) ─────────────────────────────────────────
    crm_row_id:     Optional[str]
    status:         Optional[str]  # sent | replied | booked | skip | error


class PipelineState(TypedDict):
    leads:      List[LeadState]      # All discovered leads
    qualified:  List[LeadState]      # Leads with score >= MIN_ICP_SCORE
    processed:  List[LeadState]      # Completed full pipeline
    run_date:   str
    errors:     List[str]
