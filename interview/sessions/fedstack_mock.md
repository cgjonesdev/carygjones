# Fedstack Mock Interview — Session Notes
# ========================================
# USE THE INTERVIEW PREP AGENT (tools/interview/.prompt)
# Trigger: "run interview prep fedstack" or "Full Fedstack mock interview"
#
# Answer each question out loud (2–3 min). Compare against model answers below.

## Round 1: Behavioral

### Q1. Tell me about yourself.
MODEL: Use elevator intro from fedstack.md. Hit: 15 yrs Python/API/cloud,
HIPAA + Disney scale, U.S. citizen + Marine Corps veteran, mission-critical
systems mindset, goal = federal applications via Fedstack.

### Q2. Why Fedstack / why federal technology?
MODEL: Stakes over scale — systems millions depend on. Security + reliability
match your regulated background (HIPAA, medical devices). Fedstack HTD path
into meaningful gov work. Compensation and remote align. Not chasing Big Tech
vanity metrics — want impact.

### Q3. This role requires U.S. citizenship and public trust clearance. Confirm eligibility and relevant background.
MODEL: U.S. citizen. Eligible for public trust (SF-85P process). Regulated
work: Alan Health HIPAA, Hospira FDA-style device verification. Marine Corps
— accountability under pressure. No issues anticipated; will complete paperwork
accurately and promptly.

### Q4. Walk me through CGJSoftware. Why move from consulting?
MODEL: S-Corp for B2B contracts — full ownership DB → Docker → ECS. Not a
gap. Ready for dedicated mission teams, clearance-backed work, long-term
federal placement. Recent wins: 120ms API latency, 45% throughput, LLM
integrations with guardrails.

### Q5. Describe a time you built software where security or compliance was non-negotiable.
MODEL (STAR):
- Situation: Alan Health HIPAA platform, 500k user profiles.
- Task: REST APIs with encryption, access control, audit expectations.
- Action: OAuth2, Fernet encryption, CI/CD pre-deploy checks, PR review culture.
- Result: Secure platform servicing active users; reduced merge conflicts 70% via Git workflow docs.

---

## Round 2: Python / API Technical

### Q6. Explain the N+1 query problem and how you'd fix it in Django or SQLAlchemy.
MODEL:
- List endpoint fires one query per related row (orders → users → items).
- Diagnose: Debug Toolbar / APM → 500+ queries.
- Fix: select_related (FK), prefetch_related (M2M/reverse); SQLAlchemy joinedload.
- Cache hot reads in Redis. Result: 501 → 2 queries; 4s → ~150ms.

### Q7. How would you secure secrets and credentials in a Python app deployed on AWS?
MODEL:
- Never in Git or env files in repo. Secrets Manager / SSM Parameter Store.
- ECS task IAM role (taskRoleArn) — no static AWS keys in container.
- Rotate credentials; inject at runtime. Local dev: .env gitignored only.

### Q8. When would you choose FastAPI vs Django for a new federal API?
MODEL:
- FastAPI: high-concurrency I/O, OpenAPI-first, async external calls, lightweight services.
- Django: heavy CRUD, admin panel, mature ORM/migrations, complex auth/RBAC.
- Federal: often Django for data-heavy case management; FastAPI for integration gateways.
- Both: enforce auth, audit logging, input validation (Pydantic / DRF serializers).

### Q9. How does Python's GIL affect concurrency? Threading vs multiprocessing vs asyncio?
MODEL:
- GIL: one thread runs Python bytecode at a time.
- Threading: I/O-bound — GIL released during I/O.
- Multiprocessing: CPU-bound — separate processes.
- Asyncio: cooperative I/O concurrency (FastAPI). Celery for background CPU work off request path.

---

## Round 3: System Design / Federal Scenarios

### Q10. Design a REST API for citizen data with audit requirements.
MODEL:
- Auth: OAuth2/JWT, short TTL, refresh rotation.
- RBAC on resources; field-level redaction for PII in responses.
- TLS everywhere; encrypt PII at rest.
- Audit log: user_id, action, resource, timestamp, IP → append-only store.
- Rate limiting at gateway; WAF. Deploy ECS behind ALB in private subnets.

### Q11. Agency wants LLM document classification. Architect without leaking PII.
MODEL:
- Classified doc store; embeddings in isolated vector DB.
- Redact PII before model call; use authorized endpoint (no public OpenAI for CUI).
- Confidence threshold → human review queue.
- Log metadata not raw content where policy forbids; retention per records schedule.

### Q12. Production API suddenly returns 500s. Incident response?
MODEL:
1. CloudWatch / alerts — error rate, latency, deploy correlation.
2. Logs → stack trace; check RDS, Secrets Manager, downstream deps.
3. Rollback ECS task definition if deploy-related.
4. Scale or fail over read replica if DB saturation.
5. Status comms; RCA + monitoring/CI prevention tickets.

---

## Round 4: Live Coding (practice in fedstack_coding_drill.py)

### Q13. Valid palindrome after stripping non-alphanumeric (Easy).
MODEL: Two pointers on cleaned string. O(n) time, O(n) space for cleaned array.

### Q14. Find missing number in [0..n] (Easy).
MODEL: Gauss sum n*(n+1)//2 - sum(nums). O(n) time, O(1) space.

### Q15. Implement rate limiter: max N requests per user per minute (Medium).
MODEL: Redis sliding window or token bucket; dict + deque for interview version.
Discuss distributed Redis vs in-memory for single instance.

---

## Scoring Rubric (self-assess after each answer)

| Score | Meaning |
|-------|---------|
| 3 | Structured (STAR), specific metrics, federal/security awareness |
| 2 | Correct but vague or missing result/metric |
| 1 | Knows topic but rambles or misses key detail |
| 0 | Can't answer — review that section tonight |

Target: average 2.5+ across all 15 before real interview.

---

## Questions to ask (pick 2–3)

1. Senior engineer path through HTD — training length or direct placement?
2. Typical client stacks and clearance levels at placement.
3. Technical readiness assessment format (live coding? system design? take-home?).
4. Success metrics first 90 days on client team.
