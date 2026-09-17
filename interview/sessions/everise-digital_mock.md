# Everise Digital Mock Interview — Session Guide
# =============================================
# Role: Senior Software Engineer (Technical Discovery & Planning)
# Client: Everise Digital (freelance, CTO-facing)
#
# USE THE INTERVIEW PREP AGENT (tools/interview/.prompt)
# Trigger: "run interview prep everise-digital" or "Full Everise mock"
#
# Answer out loud (2–4 min per question). Ask for model, hint, or follow-up after each.

---

## Likely format

| Round | Focus | Duration |
|-------|-------|----------|
| 1 | Intro + discovery experience | 20–30 min |
| 2 | Live scoping scenario | 25–35 min |
| 3 | Technical judgment (read code / architecture) | 15–20 min |
| 4 | Freelance logistics + rate/availability | 10 min |

---

## Round 1: Behavioral / discovery

### Q1. Tell me about yourself.
**Probe:** Why discovery/planning, not pure IC?

**MODEL:** 15 yrs software + repeated pattern of **leading discovery before build** — Alan Health HIPAA scoping, Disney cross-team specs, CGJSoftware CTO workshops. Strong Python/AWS builder who can also write scope docs and facilitate US client calls. Excited about Everise's agency model: AI + web + data platforms, fast growth, direct CTO partnership.

### Q2. Walk me through a discovery session you led. What was the output?
**MODEL (STAR):** Alan Health — vague "patient portal" ask. Ran stakeholder workshops, mapped personas, compliance constraints, produced architecture diagram + phased requirements. Engineering team picked up with minimal rework. Emphasize **written artifacts**: scope doc, assumptions, non-goals.

### Q3. How do you handle a client who doesn't know what they want?
**MODEL:** Structured questioning (problem → users → workflows → constraints). Prototype **options** not single answer: "We could do A (2 wk MVP) or B (full integration, 6 wk)." Summarize back in writing within 48 hrs. Never start build on verbal scope alone.

### Q4. Why Everise Digital, and why this freelance model?
**MODEL:** Agency doing AI + modern web at scale for US market; role matches my consulting strengths. 5–10 hrs/week fits focused discovery work; long-term collaboration potential. Want to work directly with technical leadership (CTO), not only ticket execution.

### Q5. CGJSoftware — consulting vs joining a client team?
**MODEL:** S-Corp for B2B delivery — discovery, architecture, implementation. Not leaving consulting; this **is** consulting done right with one primary partner (Everise). Can ramp hours as engagements grow.

---

## Round 2: Live scoping scenarios

### Q6. Client wants "AI to automate our internal reports." They use Google Sheets and Slack. How do you scope?
**MODEL:**
- Clarify: which reports, how often, data sources, who consumes output, accuracy requirements.
- MVP: scheduled job reads Sheets/API → LLM summarizes → posts to Slack channel with links to source rows.
- Risks: stale data, wrong numbers (require validation step), API rate limits.
- Phases: (1) one report type pilot, (2) templating + admin config, (3) optional dashboard.
- Deliverables: discovery summary, data flow diagram, acceptance criteria, hour estimate ranges.

### Q7. How do you prevent scope creep after discovery is signed off?
**MODEL:** Written SOW with in/out scope, change-order process, single backlog owner. Log all new asks; size impact before committing. Weekly sync with "decisions" doc. CTO alignment before client yes on extras.

### Q8. Sketch a high-level architecture for a B2B SaaS MVP (multi-tenant, Stripe billing, admin dashboard).
**MODEL:** React/Next frontend → REST API (Django or FastAPI) → PostgreSQL (tenant_id on rows or schema-per-tenant discussion) → Stripe webhooks → background worker for emails/exports → S3 for uploads → CI/CD. Call out auth (JWT/session), observability, and what's **deferred** (SSO, advanced analytics).

---

## Round 3: Technical judgment

### Q9. You're reviewing a proposal to rebuild a monolith as 12 microservices on day one. What's your advice?
**MODEL:** Push back — strangler fig pattern; extract highest-churn or scaling-bound modules first. Microservices tax (ops, distributed tracing, deployment complexity) rarely justified for early MVP. Document phased extraction criteria.

### Q10. How do you evaluate whether an AI feature is worth building vs a rules engine?
**MODEL:** Decision tree: Is input unstructured language? Is accuracy threshold achievable with available data? Is failure cost high (medical/legal)? If low volume or fixed rules suffice → rules first. If RAG/LLM needed → define eval set, human review loop, cost per request at scale.

---

## Round 4: Logistics

### Q11. Availability, rate, and communication preferences?
**MODEL:** Remote LA; US business hours for calls (flex PST/EST). Start 5 hrs/week as JD suggests; can scale. Rate: target $125–150/hr given senior discovery + implementation depth — open to discussion on ramp. Async updates via Slack/email; written summaries after every client call.

---

## Scoring rubric

| Score | Meaning |
|-------|---------|
| 3 | Structured (STAR or playbook), client-centric, clear deliverables & tradeoffs |
| 2 | Correct direction but vague on docs, metrics, or phasing |
| 1 | Too engineer-only or too hand-wavy — review everise-digital.md scenarios |

Target: **2.5+ average** before real call.

---

## Questions to ask (pick 3)

1. Typical discovery deliverable template you use today?
2. Split between new greenfield vs AI add-on vs legacy modernization?
3. Who builds after discovery — in-house or same contractor pool?
4. Success metrics for this role in first 60 days?
