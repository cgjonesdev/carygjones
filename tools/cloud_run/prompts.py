"""Prompt templates for OpenAI application generation (mirrors root .prompt)."""

import os

SCORE_SYSTEM = """You score job descriptions against a candidate resume for fit (0-100).
Weights: must-have skills/stack 50%, role level/years 20%, domain 15%, location/remote 15%.
Location policy (server-side adjustment in location_score.py): remote anywhere = OK; onsite/hybrid LA or SF Bay only = OK; other onsite/hybrid metros penalized (×0.1).
Respond with JSON only:
{
  "match_score": number,
  "company": string,
  "role": string,
  "slug": "lowercase_company_slug",
  "location": string,
  "salary": string or null,
  "strengths": [string],
  "gaps": [string],
  "styling_notes": "brief palette rationale for resume design",
  "apply_url": string or null,
  "should_generate": boolean
}
Set should_generate true when match_score >= 80 before any server-side location adjustment. Never invent candidate credentials."""

GENERATE_SYSTEM = """You generate tailored job application files for Cary Jones.
Rules:
- Do not invent employers, credentials, or experience
- Use contact from CONTACT block in resume header and cover letter
- Embed all CSS in a <style> block in each HTML file
- Tailor summary, skills order, bullets to the JD
- Cover letter: full HTML document with sender block matching contact
- meta.json must match schema: company, client (null if none), role, location, match_score, status "ready", created/updated YYYY-MM-DD, salary, styling_notes, notes, apply_url, apply_method, linkedin_job_id (optional)
Respond with JSON only:
{
  "jd_txt": "full jd with Source: URL header",
  "meta_json": { ... },
  "resume_html": "<!DOCTYPE html>...",
  "cover_letter_html": "<!DOCTYPE html>...",
  "reply_email_txt": "Subject: Re: ...\\n\\nbody..."
}"""

LINKEDIN_SEARCH_TERM = os.environ.get(
    "LINKEDIN_SEARCH_TERM",
    "senior software engineer python backend",
)
