from __future__ import annotations

import base64
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
    resume_format: str,
    job_title: str,
    job_text: str,
    job_url: str,
    user_notes: str,
) -> dict[str, Any]:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    prompt = f"""
Create a tailored application pack for the candidate below.

Selected resume variant: {resume_name}
Job title/page title: {job_title}
Job URL: {job_url or "Not provided"}

Candidate resume:
<<<RESUME>>>
{resume_text}
<<<END_RESUME>>>

Resume format: {resume_format}

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
- tailored_resume_content_b64: string
- output_format: string
- cover_letter: string
- cold_email: string

Rules:
- Keep the tailored resume ATS-friendly and concise.
- Preserve contact information from the resume when present.
- Encode the resume content in base64 and return it in `tailored_resume_content_b64`.
- If `resume_format` is `latex`, encode a full compile-ready LaTeX document in `tailored_resume_content_b64`.
- If `resume_format` is `latex`, preserve the class, preamble, macros, and overall document structure unless a minimal safe change is necessary.
- If `resume_format` is `latex`, do not wrap the LaTeX in markdown fences.
- If `resume_format` is not `latex`, encode markdown headings and bullets in `tailored_resume_content_b64`.
- Set `output_format` to `latex` or `markdown` accordingly.
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
        temperature=0.2,
    )

    content = response.output_text.strip()
    parsed = _parse_json(content)
    encoded_resume = parsed.get("tailored_resume_content_b64", "")
    if encoded_resume:
        parsed["tailored_resume_content"] = base64.b64decode(encoded_resume).decode("utf-8")
    else:
        parsed["tailored_resume_content"] = ""
    return parsed


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise ValueError("The model did not return valid JSON.")
        return json.loads(match.group(0))
