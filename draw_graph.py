"""
Visualize the LangGraph agent pipeline — with per-node descriptions.

LangGraph doc snippet used:
    app.get_graph().draw_mermaid_png()  -> PNG bytes via mermaid.ink API (free)
    app.get_graph().draw_mermaid()      -> raw Mermaid text
    app.get_graph().draw_ascii()        -> ASCII art (offline fallback)

The annotated diagram is built by writing custom Mermaid text and calling
the same mermaid.ink API that LangGraph uses internally.

Usage:
    python draw_graph.py
"""
import sys
import base64
import requests
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

# ── 1. ASCII fallback (offline, always works) ─────────────────────────────────
from langgraph.graph import StateGraph, END
from graph.state import PipelineState

def _build_bare_pipeline():
    def noop(s): return s
    g = StateGraph(PipelineState)
    for n in ["discover", "score", "enrich", "personalize", "outreach", "crm"]:
        g.add_node(n, noop)
    g.set_entry_point("discover")
    for a, b in [("discover","score"),("score","enrich"),("enrich","personalize"),
                 ("personalize","outreach"),("outreach","crm"),("crm", END)]:
        g.add_edge(a, b)
    return g.compile()

app = _build_bare_pipeline()
print("\n" + "="*55)
print("  LEAD GENERATION PIPELINE — ASCII")
print("="*55)
print(app.get_graph().draw_ascii())

# ── 2. Annotated Mermaid diagram ──────────────────────────────────────────────
#
# Each node box shows:
#   - Node number + name (title line)
#   - What it does (2-3 lines)
#   - Which free tools / APIs it uses
#   - What it outputs to the next node
#
ANNOTATED_MERMAID = """
flowchart TD
    classDef nodeBox  fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#1e1b4b,text-align:left
    classDef terminal fill:#7c3aed,stroke:#5b21b6,stroke-width:2px,color:#ffffff

    START(["__start__"]):::terminal

    D["<b>Node 1 — discover</b><br/>─────────────────────────────────<br/>
    Queries 5 free sources in parallel threads:<br/>
    • Reddit API  ·  HackerNews Algolia API<br/>
    • Product Hunt API  ·  GitHub Search API<br/>
    • IndieHackers web scraper<br/>
    Deduplicates leads by domain + company name<br/>
    <i>Output → raw lead dicts (company, website, signals)</i>"]:::nodeBox

    S["<b>Node 2 — score</b><br/>─────────────────────────────────<br/>
    LLM: Groq llama-3.3-70b  ·  FREE<br/>
    Reads: company info, raw signals, description<br/>
    Scores each lead 1–10 against ICP criteria:<br/>
    recently funded +3  ·  hiring devs +3<br/>
    non-tech founder +2  ·  large eng team -4<br/>
    Filter: only score >= 7 continues to Node 3<br/>
    <i>Output → qualified leads + score + hot_signals</i>"]:::nodeBox

    E["<b>Node 3 — enrich</b><br/>─────────────────────────────────<br/>
    Scrapes company website for emails + tech stack<br/>
    Email finder: permutation + SMTP verification  FREE<br/>
    Fallback: Hunter.io free tier (25/month)<br/>
    GitHub API: founder profile, location, bio<br/>
    DuckDuckGo: recent news snippets about company<br/>
    Builds personalisation hook from signals + news<br/>
    <i>Output → contact email, tech stack, hook string</i>"]:::nodeBox

    P["<b>Node 4 — personalize</b><br/>─────────────────────────────────<br/>
    LLM: Groq llama-3.3-70b  ·  FREE<br/>
    Reads: contact name, hook, tech stack, signals<br/>
    Rules: 80-120 words  ·  peer tone  ·  no buzzwords<br/>
    First line MUST reference the specific hook<br/>
    One low-friction CTA only (call / case study)<br/>
    Fallback template if LLM parse fails<br/>
    <i>Output → {email_subject, email_body} per lead</i>"]:::nodeBox

    O["<b>Node 5 — outreach</b><br/>─────────────────────────────────<br/>
    Gmail API OAuth2  ·  FREE<br/>
    Sends Email 1 (Day 0) to each qualified lead<br/>
    Hard cap: MAX_EMAILS_PER_DAY (default 20)<br/>
    Schedules Day 4 follow-up into queue<br/>
    Schedules Day 9 final note into queue<br/>
    No Gmail? Saves drafts to data/email_drafts.jsonl<br/>
    <i>Output → email_sent flag + email_sent_at timestamp</i>"]:::nodeBox

    C["<b>Node 6 — crm</b><br/>─────────────────────────────────<br/>
    Google Sheets API  ·  FREE<br/>
    Logs every lead: score, contact, email, status<br/>
    Writes follow-up queue to Sequences tab<br/>
    No Sheets? Falls back to local SQLite DB<br/>
    Logs pipeline run stats (found / qualified / sent)<br/>
    <i>Output → crm_row_id + pipeline run summary</i>"]:::nodeBox

    END_N(["__end__<br/>reply_monitor runs every 2h<br/>detects replies → cancels follow-ups"]):::terminal

    START --> D --> S --> E --> P --> O --> C --> END_N
"""

# ── 3. Render annotated PNG via mermaid.ink (same API LangGraph uses) ─────────

def render_mermaid_png(mermaid_text: str) -> bytes:
    """
    LangGraph internally calls mermaid.ink to render PNG.
    We replicate the exact same call here for the annotated diagram.
    """
    encoded = base64.urlsafe_b64encode(mermaid_text.strip().encode("utf-8")).decode("utf-8")
    url = f"https://mermaid.ink/img/{encoded}?bgColor=ffffff"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Save Mermaid source
mermaid_path = data_dir / "pipeline_annotated.md"
mermaid_path.write_text(f"```mermaid\n{ANNOTATED_MERMAID}\n```\n", encoding="utf-8")
print(f"\nAnnotated Mermaid saved  --> {mermaid_path}")

# Render PNG
png_path = data_dir / "pipeline_annotated.png"
try:
    png_bytes = render_mermaid_png(ANNOTATED_MERMAID)
    png_path.write_bytes(png_bytes)
    print(f"Annotated PNG saved      --> {png_path}")
    print("\nOpen data/pipeline_annotated.png to see the full annotated workflow.")
except Exception as e:
    print(f"\n[INFO] PNG render failed (check internet): {e}")
    print(f"You can still paste the Mermaid text from {mermaid_path} into https://mermaid.live")
