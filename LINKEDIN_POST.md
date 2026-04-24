# LinkedIn Post

---

I spent 4 hours last Saturday building something I've been putting off for months.

An AI agent that does my client outreach for me. Every. Single. Morning.

Here's what happened when I ran it today:

→ It found 23 qualified leads before I had my first cup of chai
→ Wrote a personalized cold email for each one (different email, different hook, every time)
→ Sent them automatically via Gmail
→ Scheduled follow-ups for Day 4 and Day 9
→ Updated a Google Sheet with every lead, score, and status

I didn't touch a single line of that outreach.

---

The painful truth that made me build this:

I was spending 3-4 hours every day manually searching LinkedIn, Crunchbase, and Upwork for potential clients.

Copy-pasting the same cold email template with minor tweaks.
Forgetting to follow up.
Having zero visibility into what was working.

Classic "cobbler's children have no shoes" problem — I build software for clients but wasn't using software to find them.

---

So I built it properly.

6 AI agents chained together with LangGraph:

🔍 Discover — scrapes YC directory, HackerNews, Wellfound, GitHub, BetaList in parallel
⭐ Score — Groq LLM reads each company and scores them 1-10 against my ICP
🔬 Enrich — finds the founder's email, detects their tech stack, pulls a personalization hook
✉️ Personalize — writes a unique cold email that references something specific about them
📤 Outreach — sends via Gmail, queues Day 4 and Day 9 follow-ups automatically
📊 CRM — logs everything to Google Sheets

The best part?

Total monthly cost: $0.

I replaced tools that cost $276/month (OpenAI, Crunchbase, PhantomBuster, Hunter.io, Apollo) with free alternatives. Groq gives me Llama 3.3 70B for free. YC has a public API. HackerNews has a free search API. SMTP verification finds emails without paying anyone.

---

A real email it wrote this morning (company name changed):

Subject: "Shipped reconciliation for 2 fintechs — relevant to Finflow?"

"Hi Rachel,

Congrats on the YC W25 batch — saw you're hiring backend engineers while building out the reconciliation engine.

We shipped exactly this for two US fintech startups in the last 8 months. Same stack (Node + PostgreSQL), delivered in 6 weeks.

Happy to share the case study.

Worth a 20-min call this week?

— Anwar, DevCraft"

That email was written entirely by AI. It referenced her specific YC batch, her job posting, and her tech stack.

I didn't write a single word of it.

---

Is it perfect? No.

Some emails miss the mark. Some leads have wrong emails. The enrichment sometimes fails on smaller companies.

But it runs every morning while I work on actual client projects. And it's already booked me 2 discovery calls in the first week.

---

I'm sharing the full source code on GitHub (link in comments).

Everything is open source. Take it, fork it, adapt it for your own agency.

If you're a developer running an agency and you're still doing outreach manually — you're working too hard.

Build the thing that finds your next client.

---

What's your current outreach process? Still doing it manually?

Drop a comment — genuinely curious how others are handling this.

#AI #LangGraph #LeadGeneration #ColdEmail #AgenticAI #Python #OpenSource #SoftwareDevelopment #Startup #Entrepreneurship

---

## Shorter version (if you want something punchier)

---

I built an AI agent that does my client outreach while I sleep.

Every morning it:
→ Finds 20-30 qualified leads from YC, HackerNews, Wellfound, GitHub
→ Scores them against my ICP using a free LLM (Groq)
→ Finds the founder's email without paying for any tool
→ Writes a unique personalized cold email for each one
→ Sends them. Schedules follow-ups. Updates my CRM.

I wake up to a Google Sheet full of prospects and email drafts already sent.

Total cost: $0/month.

I replaced $276/month in paid tools (Crunchbase, PhantomBuster, Apollo, Hunter.io, OpenAI) with free APIs. Groq is free. YC has a public API. HackerNews search is free. SMTP verification is free.

Built with LangGraph — 6 AI agents chained together in a pipeline.

Full source code on GitHub (link in comments). Take it and build on it.

The best client you'll ever land might be one automated email away.

#AI #Python #LangGraph #LeadGeneration #AgenticAI #OpenSource #SoftwareDevelopment

---

## Comment to pin (add as first comment on the post)

🔗 GitHub repo: [your link here]

Built with: LangGraph · LangChain · Groq (free) · Gmail API · Google Sheets

Setup takes about 20 minutes. You need one free API key (Groq) to get started.

Happy to answer any questions below 👇
