from __future__ import annotations

import json
import subprocess
import tempfile
from html import escape
from io import BytesIO
from pathlib import Path

from docx import Document


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
PDF_RENDERER = APP_DIR / "render_pdf.mjs"


def markdown_bytes(value: str) -> bytes:
    return value.encode("utf-8")


def docx_bytes(title: str, body: str) -> bytes:
    document = Document()
    document.add_heading(title, level=1)

    for block in body.split("\n"):
        line = block.rstrip()
        if not line:
            document.add_paragraph("")
            continue
        if line.startswith("# "):
            document.add_heading(line[2:].strip(), level=1)
            continue
        if line.startswith("## "):
            document.add_heading(line[3:].strip(), level=2)
            continue
        if line.startswith("### "):
            document.add_heading(line[4:].strip(), level=3)
            continue
        if line.startswith("- "):
            document.add_paragraph(line[2:].strip(), style="List Bullet")
            continue
        document.add_paragraph(line)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.read()


def pdf_bytes(title: str, body: str) -> bytes:
    html = _markdown_to_html(title=title, body=body)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / "document.html"
        output_path = tmp_path / "document.pdf"
        input_path.write_text(html, encoding="utf-8")

        command = [
            "node",
            str(PDF_RENDERER),
            str(input_path),
            str(output_path),
        ]
        subprocess.run(command, cwd=ROOT_DIR, check=True, capture_output=True, text=True)
        return output_path.read_bytes()


def _markdown_to_html(title: str, body: str) -> str:
    blocks: list[str] = []
    in_list = False

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append("<div class='spacer'></div>")
            continue

        if line.startswith("# "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h1>{escape(line[2:].strip())}</h1>")
            continue

        if line.startswith("## "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h2>{escape(line[3:].strip())}</h2>")
            continue

        if line.startswith("### "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h3>{escape(line[4:].strip())}</h3>")
            continue

        if line.startswith("- "):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{_format_inline(line[2:].strip())}</li>")
            continue

        if in_list:
            blocks.append("</ul>")
            in_list = False

        blocks.append(f"<p>{_format_inline(line)}</p>")

    if in_list:
        blocks.append("</ul>")

    styles = """
    <style>
      @page { size: A4; margin: 0.55in; }
      :root {
        --text: #172033;
        --muted: #4b5567;
        --line: #d7dce5;
        --accent: #0f766e;
      }
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text);
        line-height: 1.45;
        font-size: 11.4pt;
        margin: 0;
      }
      .page-title {
        font-size: 9pt;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--accent);
        margin-bottom: 12px;
      }
      h1, h2, h3 { margin: 0; }
      h1 {
        font-size: 19pt;
        margin-top: 18px;
        margin-bottom: 8px;
      }
      h2 {
        font-size: 12.5pt;
        margin-top: 18px;
        margin-bottom: 6px;
        padding-bottom: 3px;
        border-bottom: 1px solid var(--line);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      h3 {
        font-size: 11.6pt;
        margin-top: 12px;
        margin-bottom: 4px;
      }
      p {
        margin: 0 0 7px 0;
      }
      ul {
        margin: 6px 0 10px 18px;
        padding: 0;
      }
      li {
        margin: 0 0 4px 0;
      }
      strong { font-weight: 700; }
      em { font-style: italic; }
      .spacer {
        height: 4px;
      }
      .muted {
        color: var(--muted);
      }
    </style>
    """

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"{styles}</head><body>"
        f"<div class='page-title'>{escape(title)}</div>"
        + "".join(blocks)
        + "</body></html>"
    )


def _format_inline(value: str) -> str:
    escaped = escape(value)
    escaped = escaped.replace("**", "__BOLD__")
    escaped = escaped.replace("*", "__ITALIC__")

    parts = escaped.split("__BOLD__")
    for index in range(1, len(parts), 2):
        parts[index] = f"<strong>{parts[index]}</strong>"
    escaped = "".join(parts)

    parts = escaped.split("__ITALIC__")
    for index in range(1, len(parts), 2):
        parts[index] = f"<em>{parts[index]}</em>"
    return "".join(parts)
