# Cisco/TCS Mock Interview — Session Notes
# ==========================================
# Answer each question out loud (2–3 min). Compare against model answers below.

## Round 1: Behavioral

### Q1. Tell me about yourself.
MODEL: Use elevator intro from cisco_tcs.md. Hit: 15 yrs, Python/Django/AWS,
Fidelity DRF, Disney scale, CGJSoftware ECS, goal = Cisco enterprise team.

### Q2. Why are you interested in this role at Cisco?
MODEL: Enterprise-scale backend work, Python/Django/AWS stack match, opportunity
to work on mission-critical systems. Optional: Hospira Cisco ACS connection.

### Q3. Walk me through your experience with CGJSoftware. Why leave consulting?
MODEL: S-Corp vehicle for B2B contracts. End-to-end ownership (DB → Docker → ECS).
Ready for dedicated team, shared codebase, long-term product impact at Cisco.
Do NOT apologize. Pivot to recent wins (120ms latency, 45% throughput).

---

## Round 2: Python / Django Technical

### Q4. Explain the N+1 query problem and how you'd fix it in Django.
MODEL:
- Situation: List endpoint hits DB once per related object (orders → users → items).
- Diagnose: Debug Toolbar / APM shows 500+ queries.
- Fix: select_related('user') for FK; prefetch_related('items') for reverse/M2M.
- Result: 501 → 2 queries, 4s → 150ms.

### Q5. How does Python's GIL affect concurrency? When would you use threading vs multiprocessing vs asyncio?
MODEL:
- GIL: one thread executes Python bytecode at a time.
- Threading: I/O-bound (network, disk) — threads release GIL during I/O waits.
- Multiprocessing: CPU-bound (parsing, computation) — separate processes, separate GILs.
- Asyncio: single-threaded cooperative multitasking for high-concurrency I/O (FastAPI, aiohttp).
- Django is sync by default; use Celery for background CPU work.

### Q6. Describe how you'd deploy a Django app to AWS with zero-downtime releases.
MODEL:
- Dockerize app → ECR → ECS Fargate task definition.
- RDS PostgreSQL in private subnet; Secrets Manager for credentials.
- ALB health checks; CodeDeploy or ECS rolling/blue-green deployment.
- Static files on S3 + CloudFront.
- Migrations: run as one-off ECS task before traffic shift; expand/contract for schema changes.

---

## Round 3: System Design / Scenario

### Q7. Our external API partner rate-limits us to 100 req/min but we need 1,000. What do you do?
MODEL: Celery queue + Redis broker. Workers with rate_limit='100/m'.
Cache responses in Redis (TTL). Return 202 Accepted to user with job ID; poll or webhook for result.
Never block the synchronous request path.

### Q8. A production ECS service is down. Walk me through your incident response.
MODEL:
1. Check CloudWatch alarms / ECS service events / ALB target health.
2. Pull CloudWatch Logs for error stack traces.
3. Check recent deploys — rollback task definition if correlated.
4. Verify RDS connectivity, Secrets Manager, security groups.
5. Communicate status; post-incident RCA + add monitoring/CI gates.

---

## Round 4: Live Coding (practice in cisco_tcs_coding_drill.py)

### Q9. Given an array of n distinct integers in range [0, n], find the missing number.
MODEL: Sum formula: n*(n+1)//2 - sum(nums). O(n) time, O(1) space.
Alternative: XOR all indices and values. Discuss tradeoffs if asked.

### Q10. Implement a function to group anagrams from a list of strings.
MODEL: defaultdict with sorted-tuple key. O(n * k log k) where k = max word length.
Discuss: could use character count tuple as key for O(n * k).

---

## Scoring Rubric (self-assess after each answer)

| Score | Meaning |
|-------|---------|
| 3 | Structured (STAR), specific metrics, technical depth |
| 2 | Correct but vague or missing result/metric |
| 1 | Knows topic but rambles or misses key detail |
| 0 | Can't answer — review that section tonight |

Target: average 2.5+ across all 10 before the interview.
