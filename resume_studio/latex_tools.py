from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path


def latex_compiler_available() -> bool:
    return any(shutil.which(command) for command in ("latexmk", "pdflatex", "xelatex"))


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
    is_valid, message = validate_latex_source(source)
    if not is_valid:
        raise RuntimeError(message)

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        tex_path = workspace / f"{jobname}.tex"
        pdf_path = workspace / f"{jobname}.pdf"
        tex_path.write_text(source, encoding="utf-8")

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
        return pdf_path.read_bytes(), log.strip()


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
