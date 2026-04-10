from __future__ import annotations

import base64
import binascii
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
    parsed["tailored_resume_content"] = _decode_resume_content(parsed)
    return parsed


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        extracted = _extract_first_json_object(content)
        if not extracted:
            raise ValueError("The model did not return valid JSON.")
        return json.loads(extracted)


def _decode_resume_content(parsed: dict[str, Any]) -> str:
    encoded_resume = str(parsed.get("tailored_resume_content_b64", "") or "").strip()
    if encoded_resume:
        cleaned = re.sub(r"\s+", "", encoded_resume)
        padding = (-len(cleaned)) % 4
        cleaned = cleaned + ("=" * padding)
        try:
            return base64.b64decode(cleaned).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            pass

    raw_resume = parsed.get("tailored_resume_content")
    if isinstance(raw_resume, str) and raw_resume.strip():
        return _strip_code_fences(raw_resume)

    return ""


def _strip_code_fences(value: str) -> str:
    stripped = value.strip()
    fenced = re.match(r"^```(?:latex|tex|markdown)?\n(.*)\n```$", stripped, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return stripped


def _extract_first_json_object(content: str) -> str:
    start = content.find("{")
    if start == -1:
        return ""

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(content)):
        char = content[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start:index + 1]

    return ""
