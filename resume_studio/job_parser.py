from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def looks_like_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def fetch_job_posting(url: str, timeout: int = 20) -> dict[str, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        heading = soup.find(["h1", "h2"])
        if heading and heading.get_text(strip=True):
            title = heading.get_text(strip=True)

        body_text = soup.get_text("\n", strip=True)
        cleaned_text = _clean_text(body_text)
        if len(cleaned_text) >= 1200:
            return {
                "title": title or "Job Description",
                "source_url": url,
                "text": cleaned_text,
            }
    except requests.RequestException:
        pass

    rendered = _fetch_with_playwright(url)
    return {
        "title": rendered.get("title") or "Job Description",
        "source_url": url,
        "text": _clean_text(rendered.get("text", "")),
    }


def build_job_input(job_text: str, job_url: str) -> dict[str, str]:
    cleaned_text = _clean_text(job_text)
    if job_url.strip():
        fetched = fetch_job_posting(job_url.strip())
        if cleaned_text:
            fetched["text"] = f"{fetched['text']}\n\nAdditional pasted details:\n{cleaned_text}"
        return fetched
    return {
        "title": "Pasted Job Description",
        "source_url": "",
        "text": cleaned_text,
    }


def _clean_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()


def _fetch_with_playwright(url: str) -> dict[str, str]:
    if shutil.which("node") is None:
        raise RuntimeError("Browser rendering is unavailable in this environment.")
    script_path = Path(__file__).resolve().parent / "fetch_job.mjs"
    command = ["node", str(script_path), url]
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parent.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)
