# Paramount+ Mock Interview — Session Guide
# ==========================================
# Client: Paramount+ via LTIMindtree
# Role: Sr. AWS Python Developer — Media Platform
#
# HOW TO USE WITH CURSOR
# ----------------------
# Say any of these to start a live mock:
#   "Start Paramount mock — behavioral"
#   "Start Paramount mock — system design"
#   "Start Paramount coding challenge 1"
#   "Full Paramount mock interview"
#
# Answer out loud (2–3 min behavioral, 25–35 min coding/design).
# Ask for hints, follow-ups, or model answers after each response.

---

## Interview format (likely)

| Round | Focus | Duration |
|-------|-------|----------|
| 1 | Recruiter / HM screen | Done (LTM → Paramount+) |
| 2 | Technical — Python + AWS | 45–60 min |
| 3 | System design — media/event-driven | 45–60 min |
| 4 | Team / culture / final | 30 min |

---

## Round 1: Behavioral (Paramount+ themed)

### Q1. Tell me about yourself.
**Probe:** Disney media experience, AWS scale, why Paramount+.

**MODEL:** 15 yrs Python/AWS. Disney = media & entertainment backend, $10M+ daily metrics, 99.99% uptime. CGJSoftware = Lambda/ECS event-driven pipelines, 2.5M daily transactions. Want to build scalable media platform systems at Paramount+.

### Q2. Tell me about your Disney experience — how does it relate to streaming/media platforms?
**MODEL:** Backend modules for enterprise media/financial reporting — batch costing 8hr→45min, PostgreSQL + AWS, strict uptime. Not consumer streaming directly, but same constraints: large data volumes, pipeline reliability, cross-team integration during platform migration. Pivot: understand media org pace, data integrity, production SLAs.

### Q3. CGJSoftware — what did you actually build? Why W2 now?
**MODEL:** Consulting entity for B2B contracts — Python microservices on Lambda/ECS, event-driven messaging, CI/CD ownership. Not a gap; active delivery. Moving to W2 for long-term product team, shared codebase, Paramount-scale media platform impact.

### Q4. How do you use AI coding tools in production workflows?
**MODEL:** Cursor/Copilot/Claude for boilerplate, tests, refactors — coverage 65%→92%, delivery +35%. Never ship unreviewed AI code; enforce pytest, ruff, human review. Aligns with JD requirement.

### Q5. Describe a time you improved system reliability or performance under load.
**MODEL (STAR):** Disney batch costing OR CGJSoftware ECS latency (<120ms, +45% throughput). Situation → metric → action → result.

---

## Round 2: Python technical

### Q6. When would you use Lambda vs ECS Fargate for a Python service?
**MODEL:**
- **Lambda:** short-lived, spiky, event-triggered (S3 upload, API Gateway, SQS), low ops overhead, pay per invoke.
- **Fargate:** long-running APIs, WebSockets, sustained traffic, custom runtime deps, longer cold-start tolerance not OK.
- Hybrid: API on Fargate, async workers on Lambda.

### Q7. How do you structure a testable, reusable Lambda handler?
**MODEL:** Thin handler (event parsing) → service layer (business logic) → repository (DynamoDB/S3). Dependency injection for tests. Idempotency key from event ID. Structured logging (JSON). Environment config from env vars / Secrets Manager.

### Q8. Explain event-driven architecture for media asset ingestion.
**MODEL:** S3 upload → EventBridge/S3 notification → SQS → Lambda (validate, extract metadata) → DynamoDB catalog → Step Functions for transcoding workflow → SNS completion topic. Dead-letter queue for failures. At-least-once delivery → idempotent handlers.

### Q9. DynamoDB — design access patterns for a content catalog.
**MODEL:** PK = `CONTENT#<id>`, SK = `METADATA` | `EPISODE#<n>`. GSI1: `slug` lookup. GSI2: `genre#date` for browse. Avoid scans; design keys around read paths first. Discuss single-table vs multi-table.

### Q10. How do you handle partial failures in a Step Functions pipeline?
**MODEL:** Retry with backoff on transient errors; Catch → DLQ/SNS alert on permanent failure. Compensation steps where needed. CloudWatch metrics on state transitions. Idempotent downstream steps so replays are safe.

---

## Round 3: System design

### Q11. Design a system to process uploaded video files and make them available for streaming.
**Expect:** S3 ingest, metadata Lambda, queue, transcoding (MediaConvert or similar), CDN, catalog DB, status API.

**Follow-ups:** Large file multipart upload, duplicate upload idempotency, priority queue for premium content, cost control (spot/transcoding tiers).

### Q12. Design a rate-limited API for partner integrations (1000 req/min global, 10 req/sec per partner).
**MODEL:** API Gateway usage plans OR Redis token bucket per partner key. Async for heavy work via SQS. 429 with Retry-After header. CloudWatch dashboards per partner.

---

## Round 4: Live coding (see paramount_coding_drill.py)

| # | Problem | JD tie-in |
|---|---------|-----------|
| 1 | LRU Cache | Metadata/session cache |
| 2 | Merge overlapping intervals | Broadcast windows / schedules |
| 3 | Top K frequent titles | Popularity / analytics |
| 4 | Idempotent Lambda handler sketch | Serverless best practice |
| 5 | Rate limiter (sliding window) | API protection |
| 6 | Parse simple asset manifest | Media metadata |

Run: `python interview/sessions/paramount_coding_drill.py`

---

## Gaps to address honestly

| Gap | Pivot |
|-----|-------|
| DynamoDB depth | PostgreSQL + MongoDB exp; understand PK/SK, GSI, idempotent writes |
| CDK | CloudFormation/Terraform awareness; eager to adopt CDK for IaC |
| Step Functions | Designed async workflows with queues; Step Functions = visual orchestration |
| Media containers (MP4/HLS) | Disney media domain; understand ingest/metadata/transcode conceptually |
| C# | Python-primary; can read .NET interop if needed |

---

## Questions to ask Paramount+ interviewers

1. What does the media platform team own — ingest, catalog, playback APIs, or internal tooling?
2. Lambda-heavy vs ECS/K8s split on the team?
3. How is DynamoDB used in the content catalog?
4. CI/CD and testing expectations for serverless deploys?
5. On-site LA vs NY — hybrid flexibility?

---

## Self-scoring rubric

| Score | Meaning |
|-------|---------|
| 3 | Structured answer, metrics, tradeoffs |
| 2 | Correct but rambling or missing depth |
| 1 | Vague or wrong — review model answer |

After mock: update `applications/paramount/meta.json` notes with weak areas.
