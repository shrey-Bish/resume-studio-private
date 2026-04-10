from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI


SYSTEM_PROMPT = """You are an expert resume strategist.
You tailor resumes conservatively and truthfully.
Never invent experience, tools, metrics, employers, or education.
You may reorganize, compress, rewrite, and emphasize what already exists.
Return only valid JSON that matches the requested schema.
"""


def generate_application_pack(
    api_key: str,
    model: str,
    resume_name: str,
    resume_text: str,
    job_title: str,
    job_text: str,
    job_url: str,
    user_notes: str,
) -> dict[str, Any]:
    client = OpenAI(api_key=api_key)

    prompt = f"""
Create a tailored application pack for the candidate below.

Selected resume variant: {resume_name}
Job title/page title: {job_title}
Job URL: {job_url or "Not provided"}

Candidate resume:
<<<RESUME>>>
{resume_text}
<<<END_RESUME>>>

Job description:
<<<JOB_DESCRIPTION>>>
{job_text}
<<<END_JOB_DESCRIPTION>>>

Additional user notes:
<<<USER_NOTES>>>
{user_notes or "None"}
<<<END_USER_NOTES>>>

Return JSON with exactly these keys:
- company_name: string
- role_title: string
- fit_summary: string
- keyword_matches: array of strings, max 10
- tailored_resume_markdown: string
- cover_letter: string
- cold_email: string

Rules:
- Keep the tailored resume ATS-friendly and concise.
- Preserve contact information from the resume when present.
- Use markdown headings and bullets for the resume.
- The cover letter should be brief, around 180-250 words.
- The cold email should be short, practical, and personalized.
- If company name is unclear, use "Hiring Team".
- If role title is unclear, infer from the JD but do not overstate certainty.
"""

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.output_text.strip()
    return _parse_json(content)


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise ValueError("The model did not return valid JSON.")
        return json.loads(match.group(0))

