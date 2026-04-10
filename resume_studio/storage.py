from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "outputs"
RESUMES_PATH = DATA_DIR / "resumes.json"
GENERATIONS_PATH = DATA_DIR / "generations.json"


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not RESUMES_PATH.exists():
        RESUMES_PATH.write_text("[]", encoding="utf-8")
    if not GENERATIONS_PATH.exists():
        GENERATIONS_PATH.write_text("[]", encoding="utf-8")


def _read_json(path: Path) -> list[dict[str, Any]]:
    ensure_storage()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    ensure_storage()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_resumes(storage_config: dict[str, str]) -> list[dict[str, Any]]:
    if storage_config.get("mode") == "github":
        return _github_read_json(storage_config, storage_config["resumes_path"])
    return list_resumes()


def list_resumes() -> list[dict[str, Any]]:
    return _read_json(RESUMES_PATH)


def persist_resume(
    storage_config: dict[str, str],
    name: str,
    source_filename: str,
    text: str,
    content_type: str = "text",
    source_content: str | None = None,
) -> dict[str, Any]:
    if storage_config.get("mode") == "github":
        resumes = _github_read_json(storage_config, storage_config["resumes_path"])
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cleaned_name = name.strip() or source_filename

        existing = next((item for item in resumes if item["name"].lower() == cleaned_name.lower()), None)
        payload = {
            "name": cleaned_name,
            "source_filename": source_filename,
            "text": text.strip(),
            "content_type": content_type,
            "source_content": (source_content if source_content is not None else text).strip(),
            "updated_at": now,
        }
        if existing:
            existing.update(payload)
        else:
            resumes.append(payload)
        _github_write_json(storage_config, storage_config["resumes_path"], resumes, "Update resumes store")
        return payload

    return save_resume(name, source_filename, text, content_type=content_type, source_content=source_content)


def save_resume(
    name: str,
    source_filename: str,
    text: str,
    content_type: str = "text",
    source_content: str | None = None,
) -> dict[str, Any]:
    resumes = _read_json(RESUMES_PATH)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    cleaned_name = name.strip() or source_filename

    existing = next((item for item in resumes if item["name"].lower() == cleaned_name.lower()), None)
    payload = {
        "name": cleaned_name,
        "source_filename": source_filename,
        "text": text.strip(),
        "content_type": content_type,
        "source_content": (source_content if source_content is not None else text).strip(),
        "updated_at": now,
    }

    if existing:
        existing.update(payload)
    else:
        resumes.append(payload)

    _write_json(RESUMES_PATH, resumes)
    return payload


def delete_resume(name: str) -> None:
    resumes = _read_json(RESUMES_PATH)
    filtered = [item for item in resumes if item["name"] != name]
    _write_json(RESUMES_PATH, filtered)


def seed_resume_if_missing(name: str, source_filename: str, text: str) -> None:
    if not text.strip():
        return
    resumes = _read_json(RESUMES_PATH)
    if any(item["name"].lower() == name.lower() for item in resumes):
        return
    save_resume(name=name, source_filename=source_filename, text=text)


def seed_resume_if_missing_remote(storage_config: dict[str, str], name: str, source_filename: str, text: str) -> None:
    if not text.strip():
        return
    resumes = load_resumes(storage_config)
    if any(item["name"].lower() == name.lower() for item in resumes):
        return
    persist_resume(storage_config, name=name, source_filename=source_filename, text=text)


def load_generations(storage_config: dict[str, str]) -> list[dict[str, Any]]:
    if storage_config.get("mode") == "github":
        return _github_read_json(storage_config, storage_config["generations_path"])
    return list_generations()


def persist_generation(storage_config: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    if storage_config.get("mode") == "github":
        history = _github_read_json(storage_config, storage_config["generations_path"])
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        payload = {**payload, "created_at": now}
        history.insert(0, payload)
        _github_write_json(
            storage_config,
            storage_config["generations_path"],
            history[:50],
            "Update generations store",
        )
        return payload
    return save_generation(payload)


def persist_export_bundle(
    storage_config: dict[str, str],
    folder: str,
    files: list[tuple[str, bytes]],
) -> list[str]:
    saved_paths: list[str] = []
    for filename, payload in files:
        path = f"{folder}/{filename}"
        _github_write_file(storage_config, path, payload, f"Save export {filename}")
        saved_paths.append(path)
    return saved_paths


def save_generation(payload: dict[str, Any]) -> dict[str, Any]:
    history = _read_json(GENERATIONS_PATH)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payload = {**payload, "created_at": now}
    history.insert(0, payload)
    _write_json(GENERATIONS_PATH, history[:50])
    return payload


def list_generations() -> list[dict[str, Any]]:
    return _read_json(GENERATIONS_PATH)


def _github_read_json(storage_config: dict[str, str], path: str) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{storage_config['repo']}/contents/{path}"
    params = {"ref": storage_config["branch"]}
    response = requests.get(url, headers=_github_headers(storage_config), params=params, timeout=20)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return []


def _github_write_json(
    storage_config: dict[str, str],
    path: str,
    payload: list[dict[str, Any]],
    message: str,
) -> None:
    url = f"https://api.github.com/repos/{storage_config['repo']}/contents/{path}"
    get_response = requests.get(
        url,
        headers=_github_headers(storage_config),
        params={"ref": storage_config["branch"]},
        timeout=20,
    )

    sha = None
    if get_response.status_code == 200:
        sha = get_response.json()["sha"]
    elif get_response.status_code != 404:
        get_response.raise_for_status()

    encoded = base64.b64encode(json.dumps(payload, indent=2).encode("utf-8")).decode("utf-8")
    body: dict[str, Any] = {
        "message": message,
        "content": encoded,
        "branch": storage_config["branch"],
    }
    if sha:
        body["sha"] = sha

    put_response = requests.put(url, headers=_github_headers(storage_config), json=body, timeout=20)
    put_response.raise_for_status()


def _github_write_file(
    storage_config: dict[str, str],
    path: str,
    payload: bytes,
    message: str,
) -> None:
    url = f"https://api.github.com/repos/{storage_config['repo']}/contents/{path}"
    get_response = requests.get(
        url,
        headers=_github_headers(storage_config),
        params={"ref": storage_config["branch"]},
        timeout=20,
    )

    sha = None
    if get_response.status_code == 200:
        sha = get_response.json()["sha"]
    elif get_response.status_code != 404:
        get_response.raise_for_status()

    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(payload).decode("utf-8"),
        "branch": storage_config["branch"],
    }
    if sha:
        body["sha"] = sha

    put_response = requests.put(url, headers=_github_headers(storage_config), json=body, timeout=20)
    put_response.raise_for_status()


def _github_headers(storage_config: dict[str, str]) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {storage_config['token']}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
