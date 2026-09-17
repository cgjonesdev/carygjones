# NextEra Energy — Interview Prep (restart)

**Phone screen:** Thu Sep 10, 2026 · Michael Gonzales (US Tech) — **went well**  
**Technical screen:** **Wed Sep 30, 2026 · 3:00–3:45 PM Central** (= **1:00–1:45 PM Pacific**)  
**Title:** NEA Contractor Tech Screen - Cary Jones  
**Interviewer:** Ben Stelmach · [Ben.Stelmach@fpl.com](mailto:Ben.Stelmach@fpl.com) (FPL / NextEra)  
**Team context:** NextEra Analytics · **Jake’s** Principal/Lead engineers (per Dinesh Koraboina, Sep 17)  
**Teams:** [Join](https://teams.microsoft.com/meet/220057723582770?p=gEkVwfcmcPZS8lGaaE) · Meeting ID **220 057 723 582 770** · Passcode **WH9zV3ur**  
**Dial-in:** +1 786-633-4199,,802662961#  
**Role:** Senior Software Developer / AI Software Engineer (contract via US Tech)

**Intel (Dinesh · Sep 17 · “Final interview inputs”):** collaborative engineering discussion ~45–60 min — **not** a gotcha LeetCode screen. Gmail `1a0b04c4096cca58`.

---

## What Jake’s team actually evaluates (from Dinesh)

**Format (common pattern across recent finals):**
1. **Debug** a small Python app with a **failing unit test**
2. **Review / improve** that code (owner mindset)
3. **Production-ready** — how you’d ship it

**They care more about:** how you think + communicate than syntax or algorithms.  
**Offer winners:** engineering judgment, think past the immediate bug, talk like a teammate.

**Values that showed up in offers:** fundamentals · product thinking · ownership · cloud-native · practical problem-solving · adaptability · comfort with ambiguity · clear communication.

**Biggest advice:** *Don’t approach this like a coding challenge.*

---

## Technical round — prep plan (active · aligned to Dinesh)

| Track | Practice | Materials |
|-------|----------|-----------|
| **1 · Debug** | Failing pytest → root cause before fix; narrate assumptions | `interview/sessions/nextera_debug_drill/` |
| **2 · Code review** | After fix: improvements, design concerns, refactor, “if I owned this” | Checklist below |
| **3 · Production-ready** | CI/CD, Docker, AWS/GCP, K8s awareness, monitoring, logging, auth, DB/index, IaC | Cram + your Disney/CVS/consulting stories |
| **4 · AI workflow** | Cursor / Copilot / ChatGPT — how you use them + how you review output | Not ML research |
| **Low priority** | Pure LeetCode / DP invention | Keep warm only; not the main event |

**Session rhythm (until Sep 30):**
1. 15–25 min — debug drill (talk out loud the whole time)  
2. 10 min — “what would you improve / make production-ready?” on that same app  
3. 10 min — one production topic (SQL, AWS deploy, observability, or AI workflow) with a story  
4. Optional 10 min — light practical coding (intervals/dicts) only if energy left

**Debug habits (say these out loud):**
- Restate what the test expects vs what you see  
- Trace data flow; don’t patch symptoms  
- Name the root cause, then fix  
- Immediately expand: design, tests, deploy, monitor

**Code-review prompts to practice answering:**
- What would you improve? What concerns you about the design?
- How would you refactor? What would you do differently if you owned this?
- Cover: separation of concerns · data structures · API design · error handling · config · testing · scalability / maintainability

**Production-ready checklist (pick examples from your career):**
- CI/CD · Docker · AWS (ECS/Fargate, RDS, CloudWatch, Secrets) / GCP · K8s (honest level)  
- Monitoring / observability · logging · security / auth · DB performance / indexing · IaC  

**AI workflow (they ask successful candidates often):**
- Tools: Cursor, Copilot, ChatGPT/Claude — accelerate, don’t rubber-stamp  
- Talk: debug with AI · generate then validate · docs · research · **always review** AI code  

---

## Pre-flight (Sep 30 tech screen)

| | |
|---|---|
| **When** | Wed Sep 30, 2026 · **3:00–3:45 PM Central** (= **1:00–1:45 PM Pacific**) |
| **Teams** | [Join](https://teams.microsoft.com/meet/220057723582770?p=gEkVwfcmcPZS8lGaaE) · ID **220 057 723 582 770** · Passcode **WH9zV3ur** |
| **Interviewer** | Ben Stelmach · [Ben.Stelmach@fpl.com](mailto:Ben.Stelmach@fpl.com) |
| **Recruiters** | Dinesh Koraboina · [kdinesh@ustechsolutionsinc.com](mailto:kdinesh@ustechsolutionsinc.com) · 551-307-0233 · Roshni / Michael / Riyaz |
| **Gmail intel** | [Final interview inputs](https://mail.google.com/mail/u/0/#inbox/1a0b04c4096cca58) |
| **Resume PDF** | `applications/nextera/resume.pdf` |
| **Debug drill** | `interview/sessions/nextera_debug_drill/` |
| **Cram** | `interview/prep/nextera_cram.html` |

Join Teams **5 minutes early** (12:55 PM Pacific). Resume open. Notepad. Mic check.

---

## Role reality

The title says **AI Software Engineer**, but JD + Dinesh emphasize:

| Priority | What they want |
|----------|----------------|
| **Primary** | Strong SWE fundamentals · ownership · cloud-native delivery · Python · practical problem-solving |
| **Secondary** | AI as **dev tooling / productivity** — not ML research |

**Your pitch:** *"I'm a senior backend and cloud engineer who owns features end-to-end — debug, design, ship, operate. I use AI tooling to move faster with review and tests still on me."*

---

## 60-second intro

**Glance bullets only** (don’t memorize a script — scan these on the cram sheet):

- **Who:** Cary · Sr SWE · 15+ yrs · Python backends · SQL · AWS/GCP · legacy modernization
- **Disney:** financial reporting · $10M+/day · AWS · 99.99% uptime · batch 8h → 45m
- **CVS:** monolith → domain boundaries → microservices path · Docker integration tests
- **Fidelity:** Django REST APIs · network automation · 4h → 10m
- **Consulting:** end-to-end with product · ECS/Fargate · schema → API → CI/CD → prod
- **AI (one breath):** Cursor/Copilot · LLM pipelines when useful · not ML research
- **Close:** serious infra at scale — cloud + SQL + modernize without breaking prod

Cram sheet: `interview/prep/nextera_cram.html`

---

## Stories (glance STAR — ~90 sec each)

Same bullets live on `interview/prep/nextera_cram.html`. Scan, don’t memorize.

- **Disney (scale / SQL / AWS):**
  - S — financial reporting backends
  - T — slow month-end reconcile + uptime pressure
  - A — PG schema/queries · AWS · pipeline redesign with finance stakeholders
  - R — $10M+/day · 99.99% · batch **8h → 45m**

- **CVS (legacy → modern):**
  - S — monolith for domain migration
  - T — cut safe service boundaries
  - A — codebase analysis · DDD boundaries · Docker integration tests
  - R — clearer domains · faster local integration tests · path to microservices

- **Fidelity (API / automation):**
  - S — datacenter network provisioning
  - T — manual, error-prone, slow
  - A — Django REST APIs · junior mentorship · automate device config
  - R — setup **4h → 10m** · ~95% fewer provisioning errors

- **Consulting / CGJSoftware (ownership):**
  - S — B2B clients need cloud features + legacy kept alive
  - A — Python on ECS/Fargate · schema → API → Docker → CI/CD → prod · product partners
  - R — ship independently · straddle legacy + new without big-bang rewrites

- **AI (keep short — bonus):**
  - S — faster delivery / doc workflows
  - A — Cursor/Copilot in review+test loop · LLM/RAG when it fits
  - R — velocity up · still own review + coverage · *not* ML research

**Pick by question:** scale/SQL/cloud → Disney · legacy → CVS · APIs → Fidelity · independence → Consulting · AI → one breath

---

## Likely questions + your answers

### 1. Tell me about yourself

Use intro bullets on cram sheet, then offer **one** deep story if they probe:
- **Disney:** PostgreSQL financial backend, AWS, $10M+ daily, uptime, product/finance stakeholders
- **CVS:** Legacy monolith analysis, DDD boundaries, Docker integration tests, microservices path

### 2. Why NextEra?

> *"NextEra operates at the intersection of critical infrastructure and modern software — high reliability, long-lived systems, and real-world impact on energy. That matches how I've worked in regulated enterprise environments. The role description emphasizes cloud delivery, SQL depth, and legacy modernization, which is exactly what I do best. I'm less interested in AI for its own sake and more in shipping dependable software that keeps complex operations running."*

### 3. Legacy + modern systems experience?

> *"At CVS I analyzed a monolithic codebase and helped define domain boundaries for microservices migration, with Docker-based integration testing so teams could move safely. At Dell I refactored a legacy Python test framework — eliminated circular dependencies and cut crash rates 80%. In consulting I routinely maintain legacy services while building new cloud-native features on AWS ECS/Fargate, so I'm comfortable straddling both worlds."*

### 4. SQL / data depth?

> *"PostgreSQL is my primary database — schema design, indexing, query optimization. At Disney I co-architected reconciliation tooling that cut batch processing from eight hours to forty-five minutes through SQL aggregation and pipeline redesign. I've also worked Redshift reporting and high-volume transaction pipelines."*

### 5. Cloud experience?

> *"Production AWS — ECS/Fargate, Lambda, RDS, S3, CloudWatch, Secrets Manager. Disney financial backends on AWS at 99.99% uptime. Also GCP deployments with a 3× improvement in release frequency. Docker, CI/CD via GitHub Actions, staged rollouts."*

### 6. AI experience? (keep short — bonus skill)

> *"I integrate LLMs and AI dev tools where they improve velocity — document classification pipelines, AI-assisted test and code review with Cursor and Copilot, LangChain for structured workflows. I'm not an ML researcher; I'm an engineer who applies AI practically. Happy to go deeper on any specific use case you're exploring."*

### 7. Work with product teams independently?

> *"As consultant and Scrum Master I've owned features end-to-end — requirements with product, design, implementation, CI/CD, production support. At Alan Health I led an offshore team on HIPAA-compliant APIs. I translate business needs into shippable increments without waiting for perfect specs."*

### 8. Energy / utilities domain?

**Honest pivot:**

> *"I don't have direct utility SCADA or grid operations experience. My closest parallels are regulated, high-availability enterprise systems — Disney financial reporting, HIPAA healthcare platforms, medical device software — where accuracy, auditability, and uptime matter. I ramp quickly on domain specifics when the engineering fundamentals are solid."*

### 9. Remote / schedule?

> *"I'm in Temple City, California. I can reliably cover **7 AM to 1 PM Pacific** for your **9 AM to 3 PM CST** core overlap. Outside that window I'm flexible for async work and urgent production issues. I'll confirm exact expectations with the team."*

### 10. Rate / employment structure?

If Michael asks, or if it's clearly US Tech's job:

> *"I'm engaged through US Tech Solutions — Shaik Riyaz has been my recruiter contact. For rate and W2 vs C2C I'd align with him, but I'm targeting senior contract rates consistent with a 15-year backend engineer. I'd want to understand the full package before committing."*

**Your target:** ~$155K W2 equivalent (~$74–75/hr). Listen for their band; don't undersell on the spot.

### 11. Availability / start?

> *"I can start within about two weeks of an offer, potentially sooner depending on paperwork. I'm actively interviewing but nothing that would block a reasonable start date."*

---

## Strongest match themes

| Theme | Proof point |
|-------|-------------|
| Python backend | 15+ yrs · FastAPI, Django, Flask |
| SQL / PostgreSQL | Reconciliation 8h→45m · Fidelity Django REST · Disney financial |
| AWS cloud | ECS/Fargate · 99.99% uptime · Disney |
| Legacy modernization | CVS monolith · Dell test framework refactor |
| Product delivery | Scrum Master · Alan Health · CGJSoftware |
| Regulated enterprise | Disney finance · Alan Health HIPAA |
| AI (bonus) | LLM doc pipelines · Cursor/Copilot · LangChain |

---

## Gap pivots

| Gap | Pivot |
|-----|-------|
| No utilities/energy domain | Regulated enterprise + high uptime + audit trails |
| "AI" title vs backend reality | Align early: backend/cloud first, AI accelerates delivery |
| CST hours | Already committed to 7–1 Pacific; ask re async outside window |

---

## Questions to ask Michael (pick 4–5)

1. *"What team or initiative would I be joining, and what's the first problem you'd want this engineer to solve?"*
2. *"What's the current stack — Python framework, cloud provider, primary databases, and what legacy systems are in scope?"*
3. *"How much of the work is greenfield cloud vs maintaining or migrating legacy applications?"*
4. *"Where does AI actually show up today — production features, internal tooling, or exploratory?"*
5. *"What does success look like in the first 90 days?"*
6. *"What are the next interview steps after today?"*
7. *"Who would I work with day to day — product, ops, other engineers?"*

---

## Logistics checklist

- [ ] Ready at **8:55 AM PST** Wed Aug 12
- [ ] `applications/nextera/resume.pdf` open
- [ ] Phone charged; backup number ready
- [ ] Water, notepad, pen
- [ ] After call: email thank-you to Michael (if you have email) + note Riyaz; update meta.json

---

## If they go technical (aligned to Dinesh)

| If they ask about… | Say |
|--------------------|-----|
| Debugging | Reproduce via failing test → expected vs actual → trace path → root cause → fix → re-run. Narrate assumptions. |
| Improve / own this | Contracts/types · separate IO from logic · errors/config · tests that catch this class of bug · then scale. |
| Production-ready | Docker · CI lint/tests · ECS/Fargate · Secrets Manager · CloudWatch metrics/logs/alerts · staged rollout + rollback. Tie to Disney/consulting. |
| AI tools | Cursor/Copilot for speed; I validate with tests and review. Not ML research. |
| Monolith → services | Strangler: one boundary at a time; old app stays until proven. |
| Slow SQL | EXPLAIN ANALYZE → indexes → set-based SQL. Disney 8h → 45m. |
| Touching legacy | Analyze · integration tests · flags · rollback before prod change. |

---

## Questions to ask (pick 4–5)

1. *"What does the team own day to day — analytics pipelines, APIs, internal tools?"*
2. *"What’s the stack I’ll touch first — Python services, cloud, data stores?"*
3. *"How do you usually run this tech screen — debug exercise, then design/prod discussion?"* (shows you listened to process without claiming insider knowledge)
4. *"What does success look like in the first 90 days on Jake’s team?"*
5. *"Where does AI show up for the team — product features vs engineering productivity?"*
6. *"How do you handle legacy vs greenfield on this squad?"*
7. *"Who would I work with day to day — product, ops, other engineers?"*

---
