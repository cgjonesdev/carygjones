# Everise Digital — Interview Prep

**Role:** Senior Software Engineer (Technical Discovery & Planning)  
**Company:** Everise Digital — AI-driven systems, web apps, scalable data platforms  
**Format:** Freelance · Remote · ~5–10 hrs/week · $80–150/hr · works directly with CTO  
**Account:** cgjonesdev@gmail.com

---

## Role fit (why you)

| JD requirement | Your pivot |
|----------------|------------|
| Lead discovery & scoping calls | Alan Health HIPAA discovery; CGJSoftware CTO-facing scoping; Disney cross-team requirements |
| Translate business → build-ready plans | Fidelity network automation (4 hr → 10 min); Disney batch costing (8 hr → 45 min) |
| Architecture docs & scope definitions | Produced diagrams + specs at Disney, Alan Health, CGJSoftware |
| Bridge stakeholders ↔ engineers | Scrum Master at Alan Health; regulated environments (HIPAA, finance, medical devices) |
| Hands-on software depth (not infra-only) | Python/Django/FastAPI, APIs, SaaS, AI integrations — can read code and discuss tradeoffs |
| AI/data systems familiarity | LangChain, vector DBs, production LLM integrations at CGJSoftware |
| US client communication | Remote work with US stakeholders across Disney, Fidelity, healthcare |

---

## Elevator intro (90 sec)

> I'm a Senior Software Engineer with 15+ years building web applications, APIs, and cloud-backed systems — and a strong track record **leading technical discovery** before code gets written. At Alan Health I ran discovery and scoping for HIPAA platforms, translating clinical and business requirements into architecture docs and sprint-ready backlogs. At Disney I worked on enterprise backends processing $10M+ daily, where clear specs and cross-team alignment were critical. Through CGJSoftware I work directly with founders and CTOs on AI-driven products — scoping MVPs, writing solution outlines, and preventing scope creep with structured handoffs. I'm excited about Everise because this role is exactly that bridge: discovery, documentation, and technical judgment working alongside your CTO and US clients.

---

## CGJSoftware framing

> CGJSoftware is my S-Corp for B2B engineering and technical leadership contracts — not a gap. I own discovery through delivery: requirements workshops, architecture outlines, Python/FastAPI or Django implementation, AWS deployment, and CI/CD. I'm looking for a focused engagement where discovery and planning are the primary value — which matches this role's 5–10 hrs/week model with the CTO.

---

## Discovery & scoping playbook

Use this structure when they ask *"How would you run a discovery call?"* or give a vague client brief.

### 1. Open (5 min)
- Confirm attendees, decision authority, and success criteria for **this** engagement.
- Restate the business problem in your own words; ask them to correct you.

### 2. Problem & outcomes (15 min)
- What pain are we solving? Who uses it daily?
- What does success look in 90 days vs 12 months?
- What exists today (tools, spreadsheets, legacy app)? What's broken?

### 3. Users & workflows (15 min)
- Primary personas, critical user journeys (happy path + edge cases).
- Volume: users, transactions/day, data size, peak load.
- Integrations: auth (SSO?), payments, CRM, existing APIs.

### 4. Constraints & non-goals (10 min)
- Budget band, timeline, compliance (HIPAA, SOC2, GDPR).
- **Explicit non-goals** — what we are *not* building in v1.
- Build vs buy decisions (e.g., off-the-shelf auth vs custom).

### 5. Technical feasibility sketch (10 min)
- High-level components: frontend, API, DB, async jobs, AI layer if any.
- Risks: unknown APIs, data migration, model accuracy, third-party dependencies.
- Rough phasing: MVP → v1 → v2.

### 6. Close & next steps (5 min)
- Summarize decisions live; list open questions with owners.
- Deliverable: discovery summary + scope doc + optional architecture diagram within 48–72 hrs.

---

## Scenario: Vague client brief

**Prompt:** *"A US retail client wants an AI chatbot on their website to reduce support tickets. They have 50k monthly visitors and use Shopify. Budget ~$40k, 8 weeks. How do you scope this?"*

**MODEL answer outline:**

1. **Clarify goal:** Deflect tickets (FAQ) vs full order/support agent vs lead gen? Target deflection rate?
2. **Data sources:** Product catalog (Shopify API), KB articles, past tickets (Zendesk?), return policy PDFs.
3. **Architecture sketch:**
   - Widget on storefront → API gateway → RAG pipeline (embeddings + vector store) → LLM with guardrails.
   - Human handoff to live chat when confidence low or billing/refund topics.
   - Admin dashboard for prompt tuning and reviewing bad answers.
4. **Scope MVP (8 wk / $40k reality check):**
   - Phase 1: FAQ bot on 20 top questions, Shopify product lookup, escalation to email.
   - Out of scope v1: order modifications, account changes, multilingual.
5. **Risks:** Hallucinations on policy → cite sources; PII in chat logs → retention policy.
6. **Deliverables:** Discovery doc, architecture one-pager, phased SOW, acceptance criteria per phase.

---

## Scenario: Scope creep mid-project

**Prompt:** *"Mid-sprint the client asks for real-time inventory sync and a mobile app. Original SOW was a web dashboard only. What do you do?"*

**MODEL (STAR):**
- **Situation:** Fixed SOW; client added two large features verbally on a call.
- **Task:** Protect timeline and team without damaging relationship.
- **Action:** Document request in writing; map to impact (inventory sync = new integration + webhooks; mobile = separate codebase). Present change order with options: (A) defer to Phase 2, (B) swap lower-priority items, (C) extend timeline/budget. Facilitate CTO + client call with updated diagram.
- **Result:** Client chose Phase 2 for mobile; shipped web dashboard on time. Structured change log prevented further drift.

---

## Scenario: Explain tradeoffs to non-technical stakeholders

**Prompt:** *"Client asks: should we use PostgreSQL or MongoDB for our SaaS?"*

**MODEL:**
- Start with **their** access patterns: structured reporting vs flexible documents? Relational data (users, subscriptions, invoices)?
- PostgreSQL: ACID, joins, mature tooling, good default for SaaS billing + multi-tenant apps.
- MongoDB: flexible schema for rapid prototyping or heavy nested documents — but reporting often harder.
- Recommendation tied to their case; mention migration cost if they change later.
- **Avoid jargon without translation:** "ACID" → "transactions won't half-save if something fails."

---

## Technical depth questions (lighter — "speak the language")

### When would you recommend Django vs FastAPI?
- **Django:** Admin, auth, ORM migrations, CRUD SaaS, content-heavy apps, team knows Python web stack.
- **FastAPI:** High-concurrency APIs, webhooks, microservices, OpenAPI-first, async I/O heavy workloads.
- Discovery output: document choice with rationale, not religion.

### How do you document an architecture for handoff?
- Context diagram (users, external systems).
- Container diagram: web app, API, worker, DB, cache, object storage.
- Key API contracts (OpenAPI sketch), data entities, async flows.
- NFRs: latency targets, availability, security, observability.
- Open questions & assumptions section — critical for agency work.

### AI feature discovery checklist
- What decision does the AI make vs human-in-the-loop?
- Training/fine-tuning data available? PII constraints?
- Evaluation: how will we know answers are good enough to ship?
- Fallback when model fails or API is down.
- Cost model: tokens per user session at expected volume.

---

## Resume story map

| Topic | Story | Metric / hook |
|-------|-------|----------------|
| Discovery & docs | Alan Health HIPAA platform scoping | 500k profiles, regulated handoffs |
| Stakeholder bridge | Scrum Master + cross-functional delivery | Sprint-ready backlogs from vague asks |
| Enterprise scale | Disney financial/media backend | $10M+ daily, 99.99% uptime |
| Automation ROI | Fidelity network provisioning API | 4 hr → 10 min |
| AI systems | CGJSoftware LLM + vector integrations | Production guardrails, not demos |
| Scope control | Structured SOW + change orders | Prevent creep via written scope |

---

## Gap pivots

| Possible concern | Pivot |
|------------------|-------|
| "This isn't full-time engineering" | That's the fit — discovery is the product; I still code enough to validate feasibility and review PRs. |
| "Agency / freelance pace" | CGJSoftware is agency-style delivery today; used to fast context switches and crisp written handoffs. |
| "Peachtree City / EST hours" | Remote from LA; available US business hours (PST overlaps EST/CST for calls). |
| Rate ($80–150/hr) | Target upper band given seniority + discovery leadership; open to phased ramp at 5 hrs/week. |

---

## Questions to ask the CTO

1. What does a typical discovery engagement look like end-to-end — call count, deliverables, handoff to build team?
2. How do you currently prevent scope creep between discovery and delivery?
3. What stacks do most clients land on (React + Python API + AWS?), and where do AI projects usually fit?
4. What does success look like for this role in the first 30–60 days?
5. How are proposals validated today — do you need help sizing hours and risk buffers?
6. Ratio of greenfield vs legacy modernization vs AI add-ons to existing products?

---

## Logistics

| Item | Detail |
|------|--------|
| Status | Proposal submitted via iHire (Aug 2026) — awaiting response |
| Resume | `applications/everise-digital/resume.pdf` |
| JD | `applications/everise-digital/jd.txt` |
| Prep HTML | `interview/prep/everise-digital.html` |
| Mock session | `interview/sessions/everise-digital_mock.md` |
| Gmail thread | [Gmail](https://mail.google.com/mail/u/0/#inbox/19fd367f09960955) |

**Day-of setup:** Quiet space, camera, resume PDF, Miro/diagram tool ready to sketch live, portfolio link open.
