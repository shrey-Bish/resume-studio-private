from __future__ import annotations

import base64
import re
from collections import Counter
from typing import Any

import requests


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that",
    "the", "this", "to", "with", "will", "your", "you", "we", "our", "their", "they", "role", "team", "using",
    "build", "work", "years", "experience", "skills", "job", "about", "have", "has", "who", "what", "when",
}


def select_relevant_projects(
    token: str,
    job_text: str,
    username: str | None = None,
    repo_limit: int = 30,
    match_limit: int = 5,
) -> list[dict[str, Any]]:
    keywords = _extract_keywords(job_text)
    if not keywords:
        return []

    repos = _fetch_repositories(token=token, username=username, limit=repo_limit)
    scored: list[dict[str, Any]] = []
    for repo in repos:
        combined = _repo_text(repo)
        match_counts = Counter(word for word in keywords if re.search(rf"\b{re.escape(word)}\b", combined))
        score = sum(3 if len(word) > 6 else 2 for word in match_counts)
        if repo.get("language") and repo["language"].lower() in keywords:
            score += 2
        if not score:
            continue
        scored.append(
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "url": repo["html_url"],
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "topics": repo.get("topics", []),
                "readme_excerpt": repo.get("readme_excerpt", ""),
                "matched_keywords": list(match_counts.keys())[:8],
                "score": score,
            }
        )

    scored.sort(key=lambda item: (-item["score"], item["name"].lower()))
    return scored[:match_limit]


def format_project_context(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return ""
    blocks: list[str] = []
    for project in projects:
        parts = [
            f"Project: {project['name']}",
            f"URL: {project['url']}",
        ]
        if project.get("language"):
            parts.append(f"Language: {project['language']}")
        if project.get("topics"):
            parts.append("Topics: " + ", ".join(project["topics"][:8]))
        if project.get("description"):
            parts.append(f"Description: {project['description']}")
        if project.get("readme_excerpt"):
            parts.append(f"README excerpt: {project['readme_excerpt']}")
        if project.get("matched_keywords"):
            parts.append("Matched JD keywords: " + ", ".join(project["matched_keywords"]))
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def _extract_keywords(text: str, limit: int = 30) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{1,}", text.lower())
    filtered = [word for word in words if word not in STOPWORDS and len(word) > 2]
    counts = Counter(filtered)
    ranked = [word for word, _ in counts.most_common(limit * 3)]
    deduped: list[str] = []
    for word in ranked:
        if word not in deduped:
            deduped.append(word)
        if len(deduped) >= limit:
            break
    return deduped


def _fetch_repositories(token: str, username: str | None, limit: int) -> list[dict[str, Any]]:
    headers = _headers(token)
    if username:
        url = f"https://api.github.com/users/{username}/repos"
        params = {"sort": "updated", "per_page": min(limit, 100), "type": "owner"}
    else:
        url = "https://api.github.com/user/repos"
        params = {"sort": "updated", "per_page": min(limit, 100), "affiliation": "owner"}

    response = requests.get(url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    repos = []
    for repo in response.json():
        if repo.get("fork") or repo.get("archived"):
            continue
        details = {
            "name": repo["name"],
            "full_name": repo["full_name"],
            "html_url": repo["html_url"],
            "description": repo.get("description") or "",
            "language": repo.get("language") or "",
            "topics": repo.get("topics") or [],
        }
        details["readme_excerpt"] = _fetch_readme_excerpt(token, repo["full_name"])
        repos.append(details)
        if len(repos) >= limit:
            break
    return repos


def _fetch_readme_excerpt(token: str, full_name: str) -> str:
    url = f"https://api.github.com/repos/{full_name}/readme"
    response = requests.get(url, headers=_headers(token), timeout=15)
    if response.status_code != 200:
        return ""
    payload = response.json()
    encoded = payload.get("content", "")
    if not encoded:
        return ""
    try:
        text = base64.b64decode(encoded).decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    text = re.sub(r"`{1,3}.*?`{1,3}", " ", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
    text = re.sub(r"#+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def _repo_text(repo: dict[str, Any]) -> str:
    return " ".join(
        [
            repo.get("name", ""),
            repo.get("description", ""),
            repo.get("language", ""),
            " ".join(repo.get("topics", [])),
            repo.get("readme_excerpt", ""),
        ]
    ).lower()


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
