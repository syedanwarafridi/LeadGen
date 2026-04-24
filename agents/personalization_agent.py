"""
Node 4 — Personalization Agent
Writes a unique, hyper-personalized cold email for each enriched lead.
Uses a free LLM (Groq/Gemini). Every email is different — no templates.
"""
import os
import json
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm import get_llm
from utils.helpers import get_logger
from prompts.personalization_prompt import PERSONALIZATION_SYSTEM_PROMPT
from graph.state import PipelineState

log = get_logger(__name__)


def _parse_email_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except Exception:
        text = text.replace("'", '"')
        try:
            return json.loads(text)
        except Exception:
            return {}


def _build_context(lead: dict) -> str:
    contact = lead.get("contact") or {}
    agency_name = os.getenv("YOUR_AGENCY_NAME", "our agency")
    your_name = os.getenv("YOUR_NAME", "")
    calendly = os.getenv("YOUR_CALENDLY", "")

    lines = [
        f"Company: {lead.get('company_name', 'the company')}",
        f"Contact: {contact.get('name', 'there')}, {contact.get('role', 'Founder')}",
        f"Location: {lead.get('location', 'Unknown')} (market: {lead.get('market', 'Unknown')})",
        f"Customer type: {lead.get('customer_type', 'startup')}",
        f"ICP score: {lead.get('icp_score', 'N/A')} — {lead.get('score_reason', '')}",
        f"Hot signals: {', '.join(lead.get('hot_signals') or [])}",
        f"Tech stack: {', '.join(lead.get('tech_stack') or ['Unknown'])}",
        f"Hook / personalization angle: {lead.get('hook', '')}",
        f"Description: {lead.get('description', '')}",
        f"Source: {lead.get('source', '')} ({lead.get('source_url', '')})",
        "",
        f"Your name: {your_name}",
        f"Agency: {agency_name}",
        f"Calendly: {calendly}",
        "",
        "Write a cold email using the above. Reference the hook specifically. Be human, not salesy.",
        "Return ONLY valid JSON: {\"subject\": \"...\", \"body\": \"...\"}",
    ]
    return "\n".join(lines)


def write_email(lead: dict, llm) -> dict:
    """Write a personalized email for a single lead."""
    chain = (
        ChatPromptTemplate.from_messages([
            ("system", PERSONALIZATION_SYSTEM_PROMPT),
            ("human", "{context}"),
        ])
        | llm
        | StrOutputParser()
    )
    try:
        raw = chain.invoke({"context": _build_context(lead)})
        result = _parse_email_json(raw)

        subject = result.get("subject", "")
        body = result.get("body", "")

        if not subject or not body:
            log.warning(f"Email parse failed for {lead.get('company_name')} — using fallback")
            subject, body = _fallback_email(lead)

        return {**lead, "email_subject": subject, "email_body": body}
    except Exception as e:
        log.error(f"Personalization error for {lead.get('company_name')}: {e}")
        subject, body = _fallback_email(lead)
        return {**lead, "email_subject": subject, "email_body": body}


def _fallback_email(lead: dict) -> tuple[str, str]:
    """Minimal fallback email when LLM fails."""
    contact = lead.get("contact") or {}
    name = contact.get("name") or "there"
    first = name.split()[0] if name != "there" else name
    company = lead.get("company_name", "your company")
    your_name = os.getenv("YOUR_NAME", "")
    agency = os.getenv("YOUR_AGENCY_NAME", "our agency")
    calendly = os.getenv("YOUR_CALENDLY", "")

    subject = f"Quick note re: {company}"
    body = (
        f"Hi {first},\n\n"
        f"Came across {company} and wanted to reach out.\n\n"
        f"We build web apps, mobile apps, and SaaS products for startups — "
        f"delivered fast, at a fraction of US/UK dev costs.\n\n"
        f"Worth a quick 20-min call?\n\n"
        f"—\n{your_name}\n{agency}\n{calendly}"
    )
    return subject, body


def run_personalization(state: PipelineState) -> PipelineState:
    """LangGraph Node 4 — write personalized emails for all qualified leads."""
    log.info("=== Node 4: Personalization ===")
    qualified = state.get("qualified", [])
    errors = list(state.get("errors", []))

    if not qualified:
        log.warning("No qualified leads to personalize")
        return {**state, "errors": errors}

    llm = get_llm(temperature=0.7)
    personalized = []

    for lead in qualified:
        result = write_email(lead, llm)
        log.info(
            f"  Email drafted: {lead.get('company_name')} | "
            f"Subject: {result.get('email_subject', '')[:60]}"
        )
        personalized.append(result)

    log.info(f"Personalization complete: {len(personalized)} emails drafted")
    return {**state, "qualified": personalized, "errors": errors}
