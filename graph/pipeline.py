"""
LangGraph StateGraph — 6-node agentic pipeline.

START → discover → score → enrich → personalize → outreach → crm → END
"""
from langgraph.graph import StateGraph, END
from graph.state import PipelineState
from agents.discovery_agent import run_discovery
from agents.scoring_agent import run_scoring
from agents.enrichment_agent import run_enrichment
from agents.personalization_agent import run_personalization
from agents.outreach_agent import run_outreach
from agents.crm_agent import run_crm


def build_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("discover",    run_discovery)
    graph.add_node("score",       run_scoring)
    graph.add_node("enrich",      run_enrichment)
    graph.add_node("personalize", run_personalization)
    graph.add_node("outreach",    run_outreach)
    graph.add_node("crm",         run_crm)

    graph.set_entry_point("discover")
    graph.add_edge("discover",    "score")
    graph.add_edge("score",       "enrich")
    graph.add_edge("enrich",      "personalize")
    graph.add_edge("personalize", "outreach")
    graph.add_edge("outreach",    "crm")
    graph.add_edge("crm",         END)

    return graph.compile()


# Singleton compiled pipeline
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline
