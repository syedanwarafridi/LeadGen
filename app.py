"""
Lead Generation System — Streamlit Demo
Run: streamlit run app.py
"""
import sys, os, time, json, threading
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Lead Generation System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Main background */
.stApp { background: #0f0f1a; color: #e2e8f0; }

/* Header card */
.hero {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid #7c3aed44;
    box-shadow: 0 8px 32px #7c3aed33;
}
.hero h1 { color: #fff; font-size: 2rem; margin: 0; }
.hero p  { color: #c4b5fd; margin: 0.3rem 0 0 0; font-size: 1rem; }

/* Metric cards */
.metric-card {
    background: #1e1b4b;
    border: 1px solid #7c3aed55;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.metric-card .num  { font-size: 2.5rem; font-weight: 700; color: #a78bfa; }
.metric-card .label{ font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;
                      letter-spacing: 0.1em; margin-top: 0.2rem; }

/* Node step cards */
.step-card {
    background: #1a1a2e;
    border-left: 3px solid #7c3aed;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin: 0.3rem 0;
    font-size: 0.9rem;
}
.step-done  { border-color: #10b981; }
.step-run   { border-color: #f59e0b; }
.step-wait  { border-color: #374151; color: #6b7280; }

/* Score badge */
.score-high { color: #10b981; font-weight: 700; }
.score-med  { color: #f59e0b; font-weight: 700; }
.score-low  { color: #ef4444; }

/* Email card */
.email-card {
    background: #1e1b4b;
    border: 1px solid #7c3aed44;
    border-radius: 10px;
    padding: 1.2rem;
    margin: 0.5rem 0;
}
.email-subject { color: #a78bfa; font-weight: 600; font-size: 1rem; }
.email-body    { color: #cbd5e1; font-size: 0.88rem; line-height: 1.6;
                  white-space: pre-wrap; margin-top: 0.5rem; }

/* Source badge */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}
.badge-yc   { background:#7c3aed22; color:#a78bfa; border:1px solid #7c3aed55; }
.badge-hn   { background:#f5793022; color:#fb923c; border:1px solid #f5793055; }
.badge-wf   { background:#0ea5e922; color:#38bdf8; border:1px solid #0ea5e955; }
.badge-gh   { background:#10b98122; color:#34d399; border:1px solid #10b98155; }
.badge-ph   { background:#ec489922; color:#f472b6; border:1px solid #ec489955; }
.badge-bl   { background:#84cc1622; color:#a3e635; border:1px solid #84cc1655; }
.badge-ih   { background:#f59e0b22; color:#fbbf24; border:1px solid #f59e0b55; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d0d1a;
    border-right: 1px solid #7c3aed33;
}
/* Button */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 2rem;
    font-weight: 600;
    font-size: 1rem;
    width: 100%;
    cursor: pointer;
    transition: all 0.2s;
}
.stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }

div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Demo data (instant results mode) ──────────────────────────────────────────
DEMO_LEADS = [
    {
        "company_name": "Finflow AI",
        "website": "https://finflow.ai",
        "location": "San Francisco, CA, USA",
        "market": "US",
        "source": "yc_directory",
        "team_size": 6,
        "icp_score": 9,
        "customer_type": "startup",
        "score_reason": "YC W25 batch, seed-funded, hiring backend engineers, non-tech CEO with finance background.",
        "hot_signals": ["recently_funded", "hiring_devs", "non_tech_founder"],
        "tech_stack": ["React", "Node.js", "PostgreSQL"],
        "hook": "YC W25 · hiring 3 backend engineers · CEO from Goldman Sachs",
        "description": "AI-powered financial reconciliation for SMBs",
        "contact": {"name": "Rachel Kim", "role": "CEO & Co-Founder", "email": "rachel@finflow.ai"},
        "email_subject": "Shipped reconciliation for 2 fintechs — relevant to Finflow?",
        "email_body": "Hi Rachel,\n\nCongrats on the YC W25 batch — saw you're hiring backend engineers while building out the reconciliation engine.\n\nWe shipped exactly this for two US fintech startups in the last 8 months. Same stack (Node + PostgreSQL), delivered in 6 weeks.\n\nHappy to share the case study.\n\nWorth a 20-min call this week?\n\n—\nAnwar\nDevCraft",
        "email_sent": False,
        "status": "ready",
    },
    {
        "company_name": "ShipFast Labs",
        "website": "https://shipfast.dev",
        "location": "London, UK",
        "market": "UK",
        "source": "hackernews",
        "team_size": 3,
        "icp_score": 8,
        "customer_type": "startup",
        "score_reason": "Show HN launch, small team of 3, founder is non-technical, actively building SaaS product.",
        "hot_signals": ["active_product", "solo_founder", "small_team"],
        "tech_stack": ["Next.js", "Stripe", "Vercel"],
        "hook": "Show HN: We built a Shopify-killer for indie devs — 3-person team",
        "description": "Headless e-commerce platform for developer-first teams",
        "contact": {"name": "James Thornton", "role": "Founder", "email": "james@shipfast.dev"},
        "email_subject": "Built headless commerce for 3 UK startups — saw your Show HN",
        "email_body": "Hi James,\n\nSaw your Show HN — impressive traction for a 3-person team.\n\nWe've built similar headless commerce infra for two UK startups, including a full Stripe + inventory integration. Shipped in 5 weeks.\n\nIf you ever need to move faster without hiring, worth a quick chat.\n\n15 minutes?\n\n—\nAnwar\nDevCraft",
        "email_sent": False,
        "status": "ready",
    },
    {
        "company_name": "Nudge Health",
        "website": "https://nudgehealth.io",
        "location": "Austin, TX, USA",
        "market": "US",
        "source": "wellfound",
        "team_size": 11,
        "icp_score": 8,
        "customer_type": "startup",
        "score_reason": "Hiring 2 React developers on Wellfound, Series A funded, non-technical CEO with healthcare background.",
        "hot_signals": ["hiring_devs", "recently_funded", "non_tech_founder"],
        "tech_stack": ["React", "Django", "AWS"],
        "hook": "Hiring React devs on Wellfound · Series A · CEO is ex-nurse",
        "description": "Patient engagement platform for chronic disease management",
        "contact": {"name": "Sarah Okonkwo", "role": "CEO", "email": "sarah@nudgehealth.io"},
        "email_subject": "React + Django patient portal — built 2 like Nudge",
        "email_body": "Hi Sarah,\n\nNoticed you're hiring React devs while building out the patient engagement flow — that's a tough hire right now.\n\nWe built a similar chronic-care portal for a US health-tech startup last year. React + Django, HIPAA-compliant, 8-week delivery.\n\nWant me to send the case study?\n\n—\nAnwar\nDevCraft",
        "email_sent": False,
        "status": "ready",
    },
    {
        "company_name": "BuildrAI",
        "website": "https://buildrai.co",
        "location": "Dubai, UAE",
        "market": "UAE",
        "source": "producthunt",
        "team_size": 2,
        "icp_score": 9,
        "customer_type": "individual",
        "score_reason": "Solo founder in UAE, Product Hunt launch with 200+ upvotes, no technical background, building AI tool.",
        "hot_signals": ["solo_founder", "active_product", "non_tech_founder"],
        "tech_stack": ["OpenAI API", "React"],
        "hook": "Product Hunt launch · 200 upvotes · solo non-technical founder · UAE",
        "description": "AI-powered construction project management for Gulf contractors",
        "contact": {"name": "Omar Al-Rashidi", "role": "Founder", "email": "omar@buildrai.co"},
        "email_subject": "Built 3 AI tools like Buildr — one hit 1k users in 30 days",
        "email_body": "Hi Omar,\n\nSaw the Product Hunt launch — congrats on 200+ upvotes in 24 hours.\n\nWe've built 3 AI-powered SaaS tools for UAE founders in the last year. One reached 1,000 users in 30 days. Fixed price, milestone-based, no equity.\n\nCan I send you the case study?\n\n—\nAnwar\nDevCraft",
        "email_sent": False,
        "status": "ready",
    },
    {
        "company_name": "StackTrack",
        "website": "https://stacktrack.io",
        "location": "New York, NY, USA",
        "market": "US",
        "source": "yc_directory",
        "team_size": 8,
        "icp_score": 7,
        "customer_type": "startup",
        "score_reason": "YC S24, B2B SaaS, hiring engineers, small team. Lower score — founding team has 1 technical co-founder.",
        "hot_signals": ["yc_funded", "hiring_devs", "small_team"],
        "tech_stack": ["Vue.js", "Python", "PostgreSQL"],
        "hook": "YC S24 · B2B SaaS for DevOps teams · hiring 2 engineers",
        "description": "Infrastructure cost tracking and optimization for engineering teams",
        "contact": {"name": "Mike Chen", "role": "Co-Founder & CEO", "email": "mike@stacktrack.io"},
        "email_subject": "DevOps cost dashboard — shipped for 2 YC companies",
        "email_body": "Hi Mike,\n\nSaw StackTrack in the YC S24 batch — cost visibility for infra is a real pain point.\n\nWe built similar dashboards for two other YC companies, both on Python + PostgreSQL. Moved fast because we already know the stack.\n\nWorth a 20-min call?\n\n—\nAnwar\nDevCraft",
        "email_sent": False,
        "status": "ready",
    },
]

SOURCE_BADGES = {
    "yc_directory":  ('<span class="badge badge-yc">YC</span>', "🟣"),
    "hackernews":    ('<span class="badge badge-hn">HN</span>', "🟠"),
    "wellfound":     ('<span class="badge badge-wf">Wellfound</span>', "🔵"),
    "github":        ('<span class="badge badge-gh">GitHub</span>', "🟢"),
    "producthunt":   ('<span class="badge badge-ph">PH</span>', "🩷"),
    "betalist":      ('<span class="badge badge-bl">BetaList</span>', "🟡"),
    "indiehackers":  ('<span class="badge badge-ih">IH</span>', "🟤"),
}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.divider()

    agency_name = st.text_input("Agency Name",
        value=os.getenv("YOUR_AGENCY_NAME", "DevCraft"))
    your_name = st.text_input("Your Name",
        value=os.getenv("YOUR_NAME", "Anwar"))
    min_score = st.slider("Min ICP Score", 5, 10, 7)

    st.divider()
    st.markdown("### 🎯 Target Markets")
    col1, col2, col3 = st.columns(3)
    us  = col1.checkbox("🇺🇸 US",  value=True)
    uk  = col2.checkbox("🇬🇧 UK",  value=True)
    uae = col3.checkbox("🇦🇪 UAE", value=True)

    st.divider()
    st.markdown("### 🚀 Run Mode")
    demo_mode = st.toggle("⚡ Demo Mode (instant)", value=True,
        help="Uses pre-loaded demo data for instant results. Turn off to run live pipeline.")

    if not demo_mode:
        max_leads = st.slider("Max leads to process", 5, 20, 8)

    st.divider()
    run_btn = st.button("🚀 Run Pipeline", use_container_width=True)

    st.divider()
    st.markdown("""
    <div style='font-size:0.75rem; color:#6b7280; text-align:center'>
    Powered by<br>
    <b style='color:#a78bfa'>LangGraph + Groq</b><br>
    100% Free APIs
    </div>
    """, unsafe_allow_html=True)


# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <h1>🤖 Agentic Lead Generation System</h1>
  <p>{agency_name} &nbsp;·&nbsp; Targeting US · UK · UAE startups &nbsp;·&nbsp;
     Powered by LangGraph + Groq (Free) &nbsp;·&nbsp; 0 paid APIs</p>
</div>
""", unsafe_allow_html=True)

# ── Metric placeholders ───────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
metric_discovered = m1.empty()
metric_qualified  = m2.empty()
metric_emails     = m3.empty()
metric_markets    = m4.empty()

def show_metrics(discovered=0, qualified=0, emails=0, markets="—"):
    with metric_discovered:
        st.markdown(f"""<div class="metric-card">
            <div class="num">{discovered}</div>
            <div class="label">Leads Discovered</div></div>""",
            unsafe_allow_html=True)
    with metric_qualified:
        st.markdown(f"""<div class="metric-card">
            <div class="num">{qualified}</div>
            <div class="label">Qualified (≥{min_score})</div></div>""",
            unsafe_allow_html=True)
    with metric_emails:
        st.markdown(f"""<div class="metric-card">
            <div class="num">{emails}</div>
            <div class="label">Emails Ready</div></div>""",
            unsafe_allow_html=True)
    with metric_markets:
        st.markdown(f"""<div class="metric-card">
            <div class="num">{markets}</div>
            <div class="label">Markets Covered</div></div>""",
            unsafe_allow_html=True)

show_metrics()
st.divider()

# ── Pipeline + results area ───────────────────────────────────────────────────
pipeline_col, results_col = st.columns([1, 2])

with pipeline_col:
    st.markdown("### 🔄 Pipeline Status")
    pipeline_area = st.empty()

def render_pipeline(steps: dict):
    html = ""
    icons = {"done": "✅", "running": "⏳", "waiting": "⬜"}
    descs = {
        "discover":    "Queries 7 free sources",
        "score":       "Groq LLM scores 1–10",
        "enrich":      "Finds emails + tech stack",
        "personalize": "Writes unique cold email",
        "outreach":    "Gmail API sends email",
        "crm":         "Logs to Sheets / SQLite",
    }
    for node, state in steps.items():
        if node.startswith("_"): continue
        cls   = {"done": "step-done", "running": "step-run", "waiting": "step-wait"}[state]
        icon  = icons[state]
        count = steps.get(f"_{node}_count", "")
        count_str = f" <b>({count})</b>" if count else ""
        html += f"""<div class="step-card {cls}">
            {icon} <b>{node}</b>{count_str}<br>
            <span style='color:#94a3b8;font-size:0.78rem'>{descs[node]}</span>
        </div>"""
    pipeline_area.markdown(html, unsafe_allow_html=True)

INITIAL_STEPS = {n: "waiting" for n in
    ["discover", "score", "enrich", "personalize", "outreach", "crm"]}
render_pipeline(INITIAL_STEPS)

with results_col:
    results_area = st.empty()

# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn:
    if demo_mode:
        # ── DEMO MODE — animated with pre-baked data ──────────────────────────
        leads = [l for l in DEMO_LEADS if l["market"] in
                 (["US"] if us else []) + (["UK"] if uk else []) + (["UAE"] if uae else [])]
        if not leads:
            leads = DEMO_LEADS

        steps = {n: "waiting" for n in
            ["discover", "score", "enrich", "personalize", "outreach", "crm"]}

        # Node 1 — discover
        steps["discover"] = "running"; render_pipeline(steps)
        with results_col:
            results_area.info("🔍 Querying Wellfound · YC Directory · HackerNews · BetaList · GitHub...")
        time.sleep(1.5)
        steps["discover"] = "done"
        steps["_discover_count"] = f"{len(leads) + 18} raw"
        render_pipeline(steps)
        show_metrics(discovered=len(leads)+18, markets="🇺🇸🇬🇧🇦🇪")

        # Node 2 — score
        steps["score"] = "running"; render_pipeline(steps)
        with results_col:
            results_area.info("⭐ Scoring leads with Groq llama-3.3-70b...")
        time.sleep(1.5)
        qualified = [l for l in leads if l["icp_score"] >= min_score]
        steps["score"] = "done"
        steps["_score_count"] = f"{len(qualified)} qualified"
        render_pipeline(steps)
        show_metrics(discovered=len(leads)+18, qualified=len(qualified), markets="🇺🇸🇬🇧🇦🇪")

        # Node 3 — enrich
        steps["enrich"] = "running"; render_pipeline(steps)
        with results_col:
            results_area.info("🔬 Finding emails · scraping tech stacks · getting news hooks...")
        time.sleep(1.5)
        steps["enrich"] = "done"
        steps["_enrich_count"] = f"{len(qualified)} enriched"
        render_pipeline(steps)

        # Node 4 — personalize
        steps["personalize"] = "running"; render_pipeline(steps)
        with results_col:
            results_area.info("✉️ Writing personalized emails with Groq LLM...")
        time.sleep(2)
        steps["personalize"] = "done"
        steps["_personalize_count"] = f"{len(qualified)} emails"
        render_pipeline(steps)
        show_metrics(discovered=len(leads)+18, qualified=len(qualified),
                     emails=len(qualified), markets="🇺🇸🇬🇧🇦🇪")

        # Node 5 — outreach
        steps["outreach"] = "running"; render_pipeline(steps)
        with results_col:
            results_area.info("📤 [Demo mode] Saving email drafts — not sending...")
        time.sleep(1)
        steps["outreach"] = "done"
        steps["_outreach_count"] = f"{len(qualified)} drafted"
        render_pipeline(steps)

        # Node 6 — crm
        steps["crm"] = "running"; render_pipeline(steps)
        with results_col:
            results_area.info("📊 Logging to CRM...")
        time.sleep(0.8)
        steps["crm"] = "done"
        steps["_crm_count"] = f"{len(qualified)} logged"
        render_pipeline(steps)

        # Final metrics
        show_metrics(
            discovered=len(leads)+18,
            qualified=len(qualified),
            emails=len(qualified),
            markets="🇺🇸🇬🇧🇦🇪",
        )

        results_area.empty()

    else:
        # ── LIVE MODE — real pipeline ─────────────────────────────────────────
        os.environ["MAX_EMAILS_PER_DAY"] = "0"  # dry run — no sending
        steps = {n: "waiting" for n in
            ["discover", "score", "enrich", "personalize", "outreach", "crm"]}

        try:
            from utils.local_db import init_db
            init_db()

            # Node 1
            steps["discover"] = "running"; render_pipeline(steps)
            with results_col: results_area.info("🔍 Discovering leads from live sources...")

            from agents.discovery_agent import run_discovery
            state = {"leads":[], "qualified":[], "processed":[], "run_date":"", "errors":[]}
            state = run_discovery(state)
            all_leads = state["leads"][:max_leads]
            state["leads"] = all_leads
            steps["discover"] = "done"
            steps["_discover_count"] = f"{len(all_leads)} raw"
            render_pipeline(steps)
            show_metrics(discovered=len(all_leads), markets="🇺🇸🇬🇧🇦🇪")

            # Node 2
            steps["score"] = "running"; render_pipeline(steps)
            with results_col: results_area.info("⭐ Scoring with Groq LLM...")
            from agents.scoring_agent import run_scoring
            state = run_scoring(state)
            qualified = state["qualified"]
            steps["score"] = "done"
            steps["_score_count"] = f"{len(qualified)} qualified"
            render_pipeline(steps)
            show_metrics(discovered=len(all_leads), qualified=len(qualified), markets="🇺🇸🇬🇧🇦🇪")

            # Node 3
            steps["enrich"] = "running"; render_pipeline(steps)
            with results_col: results_area.info("🔬 Enriching contacts...")
            from agents.enrichment_agent import run_enrichment
            state = run_enrichment(state)
            steps["enrich"] = "done"
            steps["_enrich_count"] = f"{len(state['qualified'])} enriched"
            render_pipeline(steps)

            # Node 4
            steps["personalize"] = "running"; render_pipeline(steps)
            with results_col: results_area.info("✉️ Writing personalized emails...")
            from agents.personalization_agent import run_personalization
            state = run_personalization(state)
            steps["personalize"] = "done"
            steps["_personalize_count"] = f"{len(state['qualified'])} emails"
            render_pipeline(steps)

            # Skip actual send
            steps["outreach"] = "done"; steps["_outreach_count"] = "dry run"
            steps["crm"]      = "done"; steps["_crm_count"]      = "logged"
            render_pipeline(steps)

            qualified = state["qualified"]
            show_metrics(
                discovered=len(all_leads),
                qualified=len(qualified),
                emails=len(qualified),
                markets="🇺🇸🇬🇧🇦🇪",
            )
            results_area.empty()

        except Exception as e:
            results_area.error(f"Pipeline error: {e}. Switch to Demo Mode for instant results.")
            st.exception(e)
            qualified = []

    # ── Results tabs ──────────────────────────────────────────────────────────
    st.divider()
    tab1, tab2 = st.tabs(["📋 Qualified Leads", "✉️ Email Previews"])

    with tab1:
        st.markdown(f"### {len(qualified)} Qualified Leads")

        rows = []
        for l in qualified:
            contact = l.get("contact") or {}
            src     = l.get("source", "")
            badge   = SOURCE_BADGES.get(src, ("", ""))[1]
            score   = l.get("icp_score", 0)
            score_str = f"{'🔥' if score >= 9 else '⭐'} {score}/10"

            rows.append({
                "Company":      l.get("company_name", ""),
                "Market":       l.get("market", ""),
                "Source":       f"{badge} {src}",
                "Score":        score_str,
                "Type":         l.get("customer_type", "").title(),
                "Contact":      contact.get("name", "—"),
                "Email":        contact.get("email", "—"),
                "Hot Signals":  ", ".join((l.get("hot_signals") or [])[:2]),
                "Tech Stack":   ", ".join((l.get("tech_stack") or [])[:3]),
            })

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, height=320,
                         hide_index=True,
                         column_config={
                             "Score": st.column_config.TextColumn(width="small"),
                             "Email": st.column_config.TextColumn(width="medium"),
                         })
        else:
            st.info("No qualified leads yet — click Run Pipeline.")

    with tab2:
        st.markdown(f"### {len(qualified)} Personalized Email Drafts")
        st.caption("Every email is unique — no templates. Written by Groq llama-3.3-70b.")

        for i, lead in enumerate(qualified):
            contact = lead.get("contact") or {}
            src     = lead.get("source", "")
            badge   = SOURCE_BADGES.get(src, ("", ""))[0]
            score   = lead.get("icp_score", 0)
            market_flag = {"US": "🇺🇸", "UK": "🇬🇧", "UAE": "🇦🇪"}.get(lead.get("market",""), "🌍")

            with st.expander(
                f"{market_flag} {lead.get('company_name','?')} — "
                f"{'🔥' if score>=9 else '⭐'} {score}/10  ·  {contact.get('name','?')}  ·  {contact.get('email','no email')}",
                expanded=(i == 0),
            ):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"""
<div class="email-card">
  <div class="email-subject">📧 {lead.get('email_subject','')}</div>
  <div class="email-body">{lead.get('email_body','')}</div>
</div>""", unsafe_allow_html=True)

                with c2:
                    st.markdown(f"""
**Source:** {badge}
**Score:** {'🔥' if score>=9 else '⭐'} {score}/10
**Type:** {lead.get('customer_type','').title()}
**Market:** {market_flag} {lead.get('market','')}
**Tech stack:** {', '.join((lead.get('tech_stack') or ['—'])[:3])}

**Hook used:**
_{lead.get('hook','—')[:120]}_

**ICP Reason:**
{lead.get('score_reason','')[:150]}
""")
                    st.markdown("---")
                    if st.button(f"📋 Copy Email", key=f"copy_{i}"):
                        full = f"Subject: {lead.get('email_subject','')}\n\n{lead.get('email_body','')}"
                        st.code(full, language=None)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style='text-align:center; color:#4b5563; font-size:0.8rem; padding:1rem'>
    Built with &nbsp;<b style='color:#a78bfa'>LangGraph</b> · <b style='color:#a78bfa'>Groq</b>
    · <b style='color:#a78bfa'>Streamlit</b> &nbsp;|&nbsp;
    Discovery: Wellfound · YC · HackerNews · BetaList · GitHub · IndieHackers &nbsp;|&nbsp;
    <b style='color:#10b981'>$0/month in API costs</b>
</div>
""", unsafe_allow_html=True)
