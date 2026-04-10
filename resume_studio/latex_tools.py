from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path


def latex_compiler_available() -> bool:
    return any(shutil.which(command) for command in ("latexmk", "pdflatex", "xelatex"))


def normalize_latex_source(source: str) -> tuple[str, list[str]]:
    lines = source.splitlines()
    seen_packages: set[str] = set()
    notes: list[str] = []
    normalized_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        package_name = _extract_single_package_name(stripped)
        if package_name in {"hyperref", "xcolor"}:
            if package_name in seen_packages:
                notes.append(f"Removed duplicate \\usepackage for `{package_name}`.")
                continue
            seen_packages.add(package_name)
        normalized_lines.append(line)

    return "\n".join(normalized_lines), notes


def validate_latex_source(source: str) -> tuple[bool, str]:
    text = source.strip()
    if not text:
        return False, "The tailored LaTeX is empty."
    if "\\documentclass" not in text:
        return False, "The tailored LaTeX is missing `\\documentclass`."
    if "\\begin{document}" not in text:
        return False, "The tailored LaTeX is missing `\\begin{document}`."
    if "\\end{document}" not in text:
        return False, "The tailored LaTeX is missing `\\end{document}`."
    return True, ""


def compile_latex_source(source: str, jobname: str = "resume") -> tuple[bytes, str]:
    normalized_source, notes = normalize_latex_source(source)
    is_valid, message = validate_latex_source(normalized_source)
    if not is_valid:
        raise RuntimeError(message)

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        tex_path = workspace / f"{jobname}.tex"
        pdf_path = workspace / f"{jobname}.pdf"
        tex_path.write_text(normalized_source, encoding="utf-8")

        if shutil.which("latexmk"):
            command = [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"{jobname}.tex",
            ]
        elif shutil.which("pdflatex"):
            command = [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"{jobname}.tex",
            ]
        elif shutil.which("xelatex"):
            command = [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"{jobname}.tex",
            ]
        else:
            raise RuntimeError("No LaTeX compiler is available in this environment.")

        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        log = (completed.stdout or "") + "\n" + (completed.stderr or "")
        if completed.returncode != 0 or not pdf_path.exists():
            raise RuntimeError(log.strip() or "LaTeX compilation failed.")
        note_text = "\n".join(notes).strip()
        full_log = f"{note_text}\n{log.strip()}".strip() if note_text else log.strip()
        return pdf_path.read_bytes(), full_log


def pdf_preview_iframe(pdf_bytes: bytes, height: int = 680) -> str:
    encoded = base64.b64encode(pdf_bytes).decode("utf-8")
    return (
        "<iframe "
        f"src='data:application/pdf;base64,{encoded}' "
        "width='100%' "
        f"height='{height}' "
        "style='border:1px solid #d9d9d9;border-radius:12px;'>"
        "</iframe>"
    )


def _extract_single_package_name(line: str) -> str | None:
    if not line.startswith("\\usepackage"):
        return None
    if "%" in line:
        line = line.split("%", 1)[0].strip()
    import re

    match = re.match(r"\\usepackage(?:\[[^\]]*\])?\{([^{}]+)\}", line)
    if not match:
        return None
    packages = [part.strip() for part in match.group(1).split(",") if part.strip()]
    if len(packages) != 1:
        return None
    return packages[0]
