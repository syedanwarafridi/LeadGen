"""
Node 2 — Scoring Agent
Scores each lead against ICP using a free LLM (Groq/Gemini).
Filters out leads scoring below MIN_ICP_SCORE (default: 7).
"""
import os
import json
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm import get_llm
from utils.helpers import get_logger
from prompts.scoring_prompt import SCORING_SYSTEM_PROMPT
from graph.state import PipelineState

log = get_logger(__name__)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    # Find first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt cleanup: replace single quotes with double
        text = text.replace("'", '"')
        try:
            return json.loads(text)
        except Exception:
            return {}


def _build_lead_summary(lead: dict) -> str:
    parts = [
        f"Company: {lead.get('company_name', 'Unknown')}",
        f"Description: {lead.get('description', '')}",
        f"Source: {lead.get('source', '')}",
        f"Location: {lead.get('location', 'Unknown')}",
        f"Team size: {lead.get('team_size', 'Unknown')}",
        f"Website: {lead.get('website', 'N/A')}",
        f"Raw signals: {', '.join(lead.get('raw_signals', []))}",
    ]
    if lead.get("funding"):
        f = lead["funding"]
        parts.append(f"Funding: {f.get('stage', '')} ${f.get('amount', 0):,} ({f.get('date', '')})")
    return "\n".join(parts)


def score_lead(lead: dict, llm) -> dict:
    """Score a single lead. Returns the lead dict with scoring fields added."""
    chain = (
        ChatPromptTemplate.from_messages([
            ("system", SCORING_SYSTEM_PROMPT),
            ("human", "Score this lead:\n\n{lead_summary}"),
        ])
        | llm
        | StrOutputParser()
    )
    try:
        raw = chain.invoke({"lead_summary": _build_lead_summary(lead)})
        result = _parse_json_response(raw)

        if not result or "score" not in result:
            log.warning(f"Could not parse score for {lead.get('company_name')} — defaulting to 0")
            return {**lead, "icp_score": 0, "score_reason": "parse_error", "skip_reason": "LLM parse error"}

        return {
            **lead,
            "icp_score": int(result.get("score", 0)),
            "score_reason": result.get("reason", ""),
            "hot_signals": result.get("hot_signals", []),
            "customer_type": result.get("customer_type", "unknown"),
            "skip_reason": result.get("skip_reason"),
        }
    except Exception as e:
        log.error(f"Scoring error for {lead.get('company_name')}: {e}")
        return {**lead, "icp_score": 0, "score_reason": "error", "skip_reason": str(e)}


def run_scoring(state: PipelineState) -> PipelineState:
    """LangGraph Node 2 — score all leads, keep those >= MIN_ICP_SCORE."""
    log.info("=== Node 2: Scoring ===")
    leads = state.get("leads", [])
    min_score = int(os.getenv("MIN_ICP_SCORE", "7"))
    errors = list(state.get("errors", []))

    if not leads:
        log.warning("No leads to score")
        return {**state, "qualified": [], "errors": errors}

    llm = get_llm(temperature=0.0)
    scored = []
    for lead in leads:
        result = score_lead(lead, llm)
        scored.append(result)
        score = result.get("icp_score", 0)
        name = lead.get("company_name", "?")
        log.info(f"  [{score}/10] {name} — {result.get('score_reason', '')[:80]}")

    qualified = [l for l in scored if (l.get("icp_score") or 0) >= min_score]
    log.info(f"Scoring complete: {len(scored)} scored → {len(qualified)} qualified (≥{min_score})")

    return {**state, "leads": scored, "qualified": qualified, "errors": errors}
