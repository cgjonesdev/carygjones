# Fedstack — Interview Prep

**Role:** Senior Software Engineer  
**Company:** Fedstack — federal workforce transformation; Hire-Train-Deploy into FSI/agency placements  
**Location:** Remote (U.S.) · Salary up to **$197,000**  
**Account:** cgjonesdev@gmail.com  
**Eligibility:** U.S. citizenship required · public trust clearance eligible

---

## Role fit (why you)

| JD requirement | Your pivot |
|----------------|------------|
| 3+ years programming | 15+ years Python, APIs, cloud — Fidelity, Disney, CGJSoftware |
| U.S. citizenship | U.S. citizen; U.S. Marine Corps veteran (Field Wireman & Communications) |
| Public trust clearance | Cover letter states eligibility; regulated work at Alan Health (HIPAA), Hospira (FDA medical devices) |
| Python API & web development | FastAPI, Django, Sanic, Flask — Fidelity DRF automation, Alan Health REST APIs |
| Modern Federal applications | Security-first microservices, OAuth2/Fernet encryption, audit logging patterns from healthcare |
| Security, scale, reliability | Disney $10M+ daily transactions, 99.99% uptime; ECS/Fargate at CGJSoftware |
| AI in secure environments | LLM/RAG integrations with guardrails; understand PII handling and data classification |

---

## Elevator intro (60–90 sec)

> I'm a Senior Software Engineer with over 15 years building secure, scalable Python APIs and cloud infrastructure. I've delivered HIPAA-compliant healthcare platforms, enterprise financial backends at Disney processing over $10 million daily on AWS, and Django REST automation at Fidelity. I'm a U.S. citizen and Marine Corps veteran, and I'm drawn to Fedstack because federal technology demands the same rigor I've practiced in regulated environments — security, reliability, and systems millions of people depend on. I want to bring my Python microservices and cloud architecture experience to mission-critical federal applications.

---

## CGJSoftware framing

> CGJSoftware is my S-Corp for B2B engineering contracts — end-to-end delivery from architecture through AWS deployment. I'm not hiding a gap; I chose consulting to own full-stack outcomes for enterprise clients. I'm ready to channel that into a dedicated federal engineering pathway where security clearance, compliance, and national-scale impact are the norm.

---

## Federal / GovCon context (know before the call)

Fedstack uses a **Hire-Train-Deploy (HTD)** model: they recruit, may run intensive paid training (8–10 weeks for some tracks), then place engineers with federal agencies or Federal System Integrators (FSIs).

**What they evaluate:**
- Can you **think and build** under security constraints?
- Drive and ability to finish a rigorous process (not just resume keywords)
- Technical readiness for systems where **stakes > scale** (vs. Big Tech scale-first culture)

**Senior track:** Your experience may bypass or shorten training — emphasize production ownership, not bootcamp-style learning curves.

---

## Scenario questions (STAR answers)

### 1. Secure API design for sensitive data

**Q:** *"Design a REST API that serves citizen-facing data where PII must be protected and every access must be auditable."*

- **Action:** JWT/OAuth2 with short-lived tokens; RBAC at endpoint level; encrypt PII at rest (AES-256) and in transit (TLS 1.2+); structured audit logs (who, what, when, IP) to immutable store (CloudWatch + S3 with Object Lock or equivalent).
- **Federal angle:** Data classification labels; least-privilege IAM; no secrets in code — Secrets Manager / Parameter Store.
- **Result:** Alan Health HIPAA platform — 500k user profiles with OAuth2 and encryption; passed security reviews.

### 2. Handling clearance and eligibility

**Q:** *"This role requires U.S. citizenship and ability to obtain public trust clearance. Walk us through your background."*

- **Action:** Confirm citizenship; disclose any foreign contacts/travel if asked on SF-85P later; highlight clean employment history and regulated-industry work (HIPAA, medical device verification).
- **Veteran angle:** Marine Corps communications — mission-critical uptime, accountability under pressure.
- **Result:** Frame as aligned: you've already worked where mistakes have real consequences.

### 3. N+1 queries at scale

**Q:** *"A Django/FastAPI list endpoint is slow under load. Diagnose and fix."*

- **Diagnose:** APM / query logging → N+1 on related objects.
- **Fix:** `select_related` / `prefetch_related` (Django) or eager loading / joinedload (SQLAlchemy); Redis cache for hot read paths; pagination with cursor-based limits.
- **Result:** CGJSoftware — API latency under 120ms after ORM optimization and caching.

### 4. Zero-downtime deployment in regulated environment

**Q:** *"How do you deploy to production without downtime when auditors expect continuous availability?"*

- **Action:** Blue/green or rolling deploy on ECS; run DB migrations as separate one-off task before traffic shift; expand/contract schema changes; feature flags for risky logic; rollback plan documented.
- **Result:** Disney — 99.99% uptime on financial reporting; ECS/CodeDeploy patterns at CGJSoftware.

### 5. Integrating AI without leaking sensitive data

**Q:** *"Agency wants document classification with LLMs. How do you architect this safely?"*

- **Action:** Air-gapped or FedRAMP-authorized model endpoint; strip/redact PII before inference; RAG over classified corpus only; human review queue for low-confidence outputs; log prompts/responses with retention policy.
- **Your pivot:** CGJSoftware LangChain + vector search — cut manual data entry 60%; emphasize guardrails and no training on production PII.

### 6. Incident response on mission-critical system

**Q:** *"Production API returns 500s during business hours. Walk through your response."*

1. Check monitoring (CloudWatch, PagerDuty) and recent deploys.
2. Pull logs; identify error rate spike vs. single failure.
3. Roll back if deploy-correlated; otherwise scale/read replica/circuit-break downstream.
4. Communicate ETA; post-incident RCA with preventive CI/monitoring tickets.

### 7. Legacy modernization (common in federal)

**Q:** *"You inherit a monolith with poor tests. How do you modernize safely?"*

- **Strangler fig:** Carve bounded contexts into services; integration tests on critical paths first; incremental extraction (CVS-style decoupling you did).
- **Result:** CVS — Dockerized domain modules, +50% integration test speed; DDD isolation POC.

### 8. Rate limiting and abuse prevention

**Q:** *"Public-facing API gets scraped and hammered. What do you do?"*

- API gateway throttling (per IP/API key); WAF rules; Redis token bucket; async queue for heavy operations; 429 with Retry-After headers.
- **Federal angle:** DDoS considerations; FISMA-aligned logging for forensic review.

---

## Technical review checklist

### Python
- GIL, threading vs multiprocessing vs asyncio
- Type hints, Pydantic validation, pytest patterns
- Memory: generators, `.iterator()` on large QuerySets

### Web / API
- REST design, idempotency, pagination
- Django ORM performance; FastAPI async patterns
- Auth: OAuth2, JWT lifecycle, RBAC

### AWS / Cloud
- ECS Fargate, ALB, RDS, S3, Secrets Manager
- VPC basics: public/private subnets, security groups
- Observability: CloudWatch, structured logging

### Security & compliance (federal emphasis)
- Least privilege IAM; encryption at rest/transit
- Audit trails; secrets never in Git
- NIST / FedRAMP awareness (high level — authorized boundaries, continuous monitoring)
- Public trust vs. secret clearance (you need public trust for this role)

---

## Gap pivots

| Potential concern | Pivot |
|-------------------|-------|
| No direct federal agency experience | Regulated healthcare (HIPAA) + medical device verification (Hospira); security-first delivery maps to federal constraints |
| CGJSoftware / consulting | S-Corp B2B vehicle; full ownership; seeking long-term mission impact via Fedstack placement |
| AI-heavy resume vs. federal caution | Emphasize guardrails, on-prem/air-gapped options, audit logging — not "move fast break things" |
| Training program anxiety | Senior with 15 yrs — ready to demonstrate technical readiness immediately; training as optional accelerator not blocker |

---

## Questions to ask Fedstack

1. *"After technical screening, what does the Hire-Train-Deploy path look like for senior engineers with 10+ years — is there a shortened track or direct client placement?"*
2. *"Which FSIs or agency domains do you most often place Senior Software Engineers into (health, finance, defense civilian)?"*
3. *"What stack and clearance level do typical client projects require on day one?"*
4. *"How do you measure success during the technical readiness assessment?"*
5. *"What does mentorship and ongoing compliance training look like once placed on a client team?"*

---

## Resume story map (STAR anchors)

| Topic | Your story | Key metric |
|-------|-----------|------------|
| Secure APIs | Alan Health — HIPAA REST platform | 500k user profiles |
| Scale / reliability | Disney — financial backend | $10M+ daily, 99.99% uptime |
| Python automation | Fidelity — network device API | 4 hr → 10 min provisioning |
| Microservices | CGJSoftware — ECS/Fargate | <120ms latency, +45% throughput |
| Regulated QA | Hospira — infusion pump verification | FDA-style verification, Cisco ACS wireless |
| Service / mission | USMC — field communications | 100% mission comm uptime |
| Legacy modernize | CVS — monolith decoupling | +50% integration test speed |

---

## Pre-flight logistics

| Item | Detail |
|------|--------|
| **Status** | Application in progress — confirm next step (recruiter screen vs. technical assessment) |
| **Citizenship** | Have passport/citizenship documentation ready if HR requests |
| **Clearance** | SF-85P may follow offer — gather 7-year residence/employment history in advance |
| **Resume PDF** | `applications/fedstack/resume.pdf` |
| **Environment** | Quiet space, stable internet, camera/mic test; code editor ready if live coding |
| **Mindset** | Emphasize **stakes, security, reliability** — Fedstack's brand vs. generic startup pitch |

**Recruiting contact:** recruiting@fedstack.com

---

## Mock session modes

| Mode | Focus |
|------|-------|
| `behavioral` | Citizenship, mission fit, CGJSoftware, STAR stories |
| `technical` | Python, Django/FastAPI, AWS, security patterns |
| `system design` | Secure API + audit logging; AI doc classification in gov environment |
| `coding` | `interview/sessions/fedstack_coding_drill.py` |
| `full mock` | behavioral → technical → design → one coding problem |

Trigger: `run interview prep fedstack` or `Full Fedstack mock interview`
