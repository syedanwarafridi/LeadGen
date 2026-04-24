# 🤖 Agentic Lead Generation System

> An autonomous AI pipeline that finds, scores, enriches, and cold-emails qualified leads — every morning — with **zero paid APIs**.

Built with **LangGraph · LangChain · Groq (free LLM) · Gmail API · Google Sheets**

---

## What It Does

Most agencies spend 3–5 hours a day manually prospecting on LinkedIn, writing cold emails, and tracking follow-ups. This system does all of that autonomously.

Every morning it:
1. **Discovers** 50–100 leads from 7 free sources (YC, HackerNews, Wellfound, GitHub, ProductHunt, BetaList, IndieHackers)
2. **Scores** each lead 1–10 against your Ideal Client Profile using a free LLM
3. **Enriches** qualified leads — finds founder email, detects tech stack, builds a personalization hook
4. **Writes** a unique, hyper-personalized cold email per lead (no templates)
5. **Sends** via Gmail API and schedules Day 4 + Day 9 follow-ups
6. **Logs** everything to Google Sheets (or local SQLite as fallback)
7. **Monitors** your inbox every 2 hours and stops follow-ups when someone replies

---

## Demo

![Pipeline Demo](data/pipeline_annotated.png)

---

## Architecture — 6-Node LangGraph Pipeline

```
START
  │
  ▼
[ discover ]   ←  Wellfound · YC · HackerNews · GitHub · BetaList · PH · IndieHackers
  │
  ▼
[ score ]      ←  Groq llama-3.3-70b scores each lead 1–10 vs ICP · filters < 7
  │
  ▼
[ enrich ]     ←  Email finder (SMTP verify) · website scraper · tech stack · news hook
  │
  ▼
[ personalize ]←  LLM writes unique 80–120 word cold email referencing specific hook
  │
  ▼
[ outreach ]   ←  Gmail API sends Email 1 · queues Day 4 + Day 9 follow-ups
  │
  ▼
[ crm ]        ←  Google Sheets logger · SQLite fallback · pipeline run stats
  │
  ▼
END  +  reply_monitor polls inbox every 2h → cancels follow-ups on reply
```

---

## Tech Stack

| Layer | Technology | Cost |
|---|---|---|
| LLM (scoring + email writing) | Groq `llama-3.3-70b-versatile` | **Free** |
| LLM fallback | Google Gemini Flash | **Free** |
| Agent orchestration | LangGraph + LangChain | **Free** |
| Lead discovery | Reddit · HN · YC · GitHub · Wellfound · BetaList | **Free** |
| Email finding | SMTP verification + Hunter.io free tier | **Free** |
| Email sending | Gmail API (OAuth2) | **Free** |
| CRM | Google Sheets API | **Free** |
| Local storage | SQLite | **Free** |
| Demo UI | Streamlit | **Free** |
| **Total monthly cost** | | **$0** |

> The original blueprint used OpenAI ($80/mo), Crunchbase ($29/mo), PhantomBuster ($69/mo), Hunter.io ($49/mo), Apollo ($49/mo) = **$276/month**. This system replaces all of them for free.

---

## Project Structure

```
lead_generation/
├── agents/
│   ├── discovery_agent.py       # Node 1 — 7 parallel sources
│   ├── scoring_agent.py         # Node 2 — Groq ICP scoring
│   ├── enrichment_agent.py      # Node 3 — email + context
│   ├── personalization_agent.py # Node 4 — LLM email writer
│   ├── outreach_agent.py        # Node 5 — Gmail sender
│   └── crm_agent.py             # Node 6 — Sheets / SQLite
├── tools/
│   ├── wellfound_tool.py        # Wellfound job listings scraper
│   ├── yc_tool.py               # YC company directory (Algolia API)
│   ├── betalist_tool.py         # BetaList new launches scraper
│   ├── hackernews_tool.py       # HN Algolia API
│   ├── producthunt_tool.py      # Product Hunt API + scrape fallback
│   ├── github_tool.py           # GitHub Search API
│   ├── email_finder_tool.py     # SMTP verify + Hunter.io
│   ├── gmail_tool.py            # Gmail send + reply detection
│   ├── sheets_tool.py           # Google Sheets R/W
│   └── scraper_tool.py          # Generic website scraper
├── graph/
│   ├── state.py                 # LangGraph PipelineState + LeadState
│   └── pipeline.py              # StateGraph definition
├── prompts/
│   ├── scoring_prompt.py        # ICP scoring system prompt
│   └── personalization_prompt.py# Email writing system prompt
├── scheduler/
│   └── run_pipeline.py          # Entry point — CLI + scheduler
├── monitor/
│   └── reply_monitor.py         # Gmail reply poller (every 2h)
├── utils/
│   ├── llm.py                   # Groq / Gemini selector
│   ├── helpers.py               # Shared utilities
│   ├── local_db.py              # SQLite CRM fallback
│   └── gmail_auth.py            # One-time OAuth setup
├── config/
│   └── icp_config.yaml          # ICP rules + discovery config
├── app.py                       # Streamlit demo UI
├── draw_graph.py                # Pipeline diagram generator
├── .env.example                 # Environment variable template
└── requirements.txt
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/yourusername/lead-gen-agent.git
cd lead-gen-agent
pip install -r requirements.txt
```

### 2. Set up environment

```bash
cp .env.example .env
```

Open `.env` and fill in at minimum:

```env
GROQ_API_KEY=gsk_...          # free at console.groq.com
YOUR_AGENCY_NAME=YourAgency
YOUR_NAME=YourName
YOUR_EMAIL=you@gmail.com
```

### 3. Run

```bash
# Phase 1 — test with manual lead input (no other keys needed)
python scheduler/run_pipeline.py --manual

# Full pipeline — dry run (discovers + scores + writes emails, no sending)
python scheduler/run_pipeline.py --dry-run

# Full pipeline — live (sends emails via Gmail)
python scheduler/run_pipeline.py

# Daily scheduler — runs at 8 AM UTC every day
python scheduler/run_pipeline.py --schedule

# Demo UI
streamlit run app.py
```

---

## API Keys Required

| Key | Where to get | Required? |
|---|---|---|
| `GROQ_API_KEY` | console.groq.com — free | **Yes** |
| `GITHUB_TOKEN` | github.com/settings/tokens — free | Recommended |
| `GMAIL_CLIENT_ID/SECRET/REFRESH` | console.cloud.google.com — free | For sending |
| `GOOGLE_SHEETS_ID` | sheets.google.com — free | Optional |
| `HUNTER_API_KEY` | hunter.io — 25 free/month | Optional |
| `PRODUCTHUNT_TOKEN` | producthunt.com/v2/oauth — free | Optional |

> Run `python utils/gmail_auth.py` once to generate your `GMAIL_REFRESH_TOKEN`.

---

## ICP Configuration

Edit `config/icp_config.yaml` to tune your Ideal Client Profile:

```yaml
scoring:
  min_score: 7           # only leads scoring 7+ proceed
  weights:
    recently_funded: 3   # +3 if funded < 90 days
    hiring_devs: 3       # +3 if posting dev job listings
    non_tech_founder: 2  # +2 if CEO has no engineering background
    large_eng_team: -4   # -4 if 20+ engineers on LinkedIn
    is_agency: -5        # -5 if company is itself an agency

targets:
  geographies: [US, UK, UAE]
  customer_types: [startup, smb, individual]
```

---

## Email Sequence

| Touch | Timing | Style |
|---|---|---|
| Email 1 | Day 0 | Personalized intro — specific hook, one CTA |
| Email 2 | Day 4 | Short follow-up — "wanted to make sure this reached you" |
| Email 3 | Day 9 | Final note — relevant case study or insight |
| Stop | Any day | Reply detected → sequence cancelled automatically |

---

## Expected Results (Month 1)

| Metric | Target |
|---|---|
| Leads discovered / day | 50–100 |
| Leads qualified (score ≥ 7) | 15–25 / day |
| Emails sent / day | 10–20 |
| Reply rate | 3–8% |
| Discovery calls / week | 1–2 |

---

## Visualize the Pipeline

```bash
python draw_graph.py
```

Generates `data/pipeline_annotated.png` — a full diagram with per-node descriptions.

---

## License

MIT — use it, modify it, build on it.

---

*Built for a Pakistani software agency targeting US · UK · UAE clients. Adapted from a LangGraph + OpenAI blueprint — rebuilt entirely on free APIs.*
