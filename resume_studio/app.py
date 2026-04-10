from __future__ import annotations

import os
from pathlib import Path
import sys

import streamlit as st
import streamlit.components.v1 as components

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from resume_studio.ai_client import generate_application_pack
from resume_studio.exporters import docx_bytes, markdown_bytes, pdf_bytes, zip_bytes
from resume_studio.job_parser import build_job_input, extract_resume_text
from resume_studio.latex_tools import compile_latex_source, latex_compiler_available, pdf_preview_iframe
from resume_studio.storage import (
    load_generations,
    load_resumes,
    persist_export_bundle,
    persist_generation,
    persist_resume,
)


st.set_page_config(
    page_title="Resume Studio",
    page_icon=":briefcase:",
    layout="wide",
)


def bootstrap() -> None:
    return


def main() -> None:
    bootstrap()
    st.title("Resume Studio")
    st.caption("Store multiple base resumes, paste a JD or job link, and generate a tailored resume, cover letter, and cold email.")

    storage_config = {
        "mode": "github",
        "repo": _secret("GITHUB_REPO", "shrey-Bish/resume-studio-private").strip(),
        "branch": _secret("GITHUB_BRANCH", "main").strip() or "main",
        "token": _secret("GITHUB_TOKEN").strip(),
        "resumes_path": "storage/resumes.json",
        "generations_path": "storage/generations.json",
    }
    api_key = _secret("GROQ_API_KEY").strip()

    with st.sidebar:
        st.subheader("Workspace")
        st.caption(f"GitHub storage: `{storage_config['repo']}`")
        st.caption(f"Branch: `{storage_config['branch']}`")

        model = st.selectbox(
            "Model",
            options=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct"],
            index=0,
        )

        st.subheader("Tips")
        st.markdown(
            "- Upload your 3 base resumes first.\n"
            "- Paste either a JD, a link, or both.\n"
            "- Add notes like tone, visa mention, or preferred project emphasis."
        )

    if not storage_config["repo"] or not storage_config["token"]:
        st.error("GitHub storage is required. Add `GITHUB_REPO` and `GITHUB_TOKEN` to Streamlit secrets.")
        return

    if not api_key:
        st.error("Add `GROQ_API_KEY` to Streamlit secrets to generate tailored documents.")
        return

    tab_library, tab_generate, tab_history = st.tabs(["Resume Library", "Tailor for a Job", "Recent Generations"])

    with tab_library:
        render_resume_library(storage_config)

    with tab_generate:
        render_generation_tab(api_key=api_key, model=model, storage_config=storage_config)

    with tab_history:
        render_history(storage_config)


def render_resume_library(storage_config: dict[str, str]) -> None:
    st.subheader("Base Resume Library")
    st.markdown("Upload files or paste raw LaTeX and save it as a resume variant.")
    uploads = st.file_uploader(
        "Upload resumes",
        type=["pdf", "docx", "doc", "txt", "md", "tex"],
        accept_multiple_files=True,
        help="Recommended names: AI+SE, SE, and DE. Upload `.tex` if you want LaTeX tailoring and compilation.",
    )

    if uploads:
        for upload in uploads:
            raw_text = upload.getvalue().decode("utf-8", errors="ignore") if upload.name.lower().endswith(".tex") else ""
            extracted_text = raw_text if upload.name.lower().endswith(".tex") else extract_resume_text(upload.name, upload.getvalue())
            content_type = "latex" if upload.name.lower().endswith(".tex") else "text"
            suggested_name = Path(upload.name).stem
            with st.expander(f"Import {upload.name}", expanded=False):
                custom_name = st.text_input(
                    "Resume label",
                    value=suggested_name,
                    key=f"label-{upload.name}",
                )
                st.text_area(
                    "Extracted text preview",
                    value=extracted_text[:4000],
                    height=220,
                    key=f"preview-{upload.name}",
                )
                if st.button("Save resume", key=f"save-{upload.name}", type="primary"):
                    persist_resume(
                        storage_config,
                        custom_name,
                        upload.name,
                        extracted_text,
                        content_type=content_type,
                        source_content=raw_text if content_type == "latex" else extracted_text,
                    )
                    st.success(f"Saved {custom_name}")
                    st.rerun()

    with st.expander("Paste LaTeX resume", expanded=False):
        pasted_name = st.text_input("Resume label", value="latex-resume", key="pasted-latex-name")
        pasted_filename = st.text_input("Source filename", value="resume.tex", key="pasted-latex-filename")
        pasted_latex = st.text_area(
            "Paste LaTeX source",
            height=260,
            placeholder="Paste your full .tex resume source here...",
            key="pasted-latex-content",
        )
        if st.button("Save pasted LaTeX", type="primary", key="save-pasted-latex"):
            if not pasted_latex.strip():
                st.error("Paste some LaTeX first.")
            else:
                persist_resume(
                    storage_config,
                    pasted_name,
                    pasted_filename,
                    pasted_latex,
                    content_type="latex",
                    source_content=pasted_latex,
                )
                st.success(f"Saved {pasted_name}")
                st.rerun()

    resumes = load_resumes(storage_config)
    if not resumes:
        st.info("No resumes saved yet. Upload your base resumes to get started.")
        return

    for resume in resumes:
        content_type = resume.get("content_type", "text")
        with st.expander(f"{resume['name']}  |  {resume['source_filename']}  |  {content_type}"):
            st.caption(f"Updated: {resume['updated_at']}")
            st.text_area(
                "Resume text",
                value=resume.get("source_content", resume["text"]),
                height=240,
                key=f"resume-{resume['name']}",
            )


def render_generation_tab(api_key: str, model: str, storage_config: dict[str, str]) -> None:
    resumes = load_resumes(storage_config)
    if not resumes:
        st.warning("Upload at least one resume in the Resume Library first.")
        return

    st.subheader("Job Input")
    selected_resume_name = st.selectbox("Which resume should be tailored?", [r["name"] for r in resumes])
    selected_resume = next(item for item in resumes if item["name"] == selected_resume_name)
    selected_format = selected_resume.get("content_type", "text")
    if selected_format == "latex":
        st.info("This resume will be tailored as LaTeX and compiled to a real PDF preview when the compiler is available.")

    col1, col2 = st.columns(2)
    with col1:
        job_url = st.text_input("Job posting URL", placeholder="https://company.com/jobs/123")
    with col2:
        user_notes = st.text_input(
            "Extra notes",
            placeholder="Mention visa sponsorship, emphasize backend work, keep tone crisp...",
        )

    job_text = st.text_area(
        "Paste job description",
        height=260,
        placeholder="Paste the job description here if you have it.",
    )

    if st.button("Generate tailored pack", type="primary"):
        if not api_key:
            st.error("Add your Groq API key in Streamlit secrets.")
            return

        if not job_url.strip() and not job_text.strip():
            st.error("Paste a job description, a job URL, or both.")
            return

        with st.spinner("Fetching the job details and generating your documents..."):
            try:
                job_input = build_job_input(job_text=job_text, job_url=job_url)
                result = generate_application_pack(
                    api_key=api_key,
                    model=model,
                    resume_name=selected_resume["name"],
                    resume_text=selected_resume.get("source_content", selected_resume["text"]),
                    resume_format=selected_format,
                    job_title=job_input["title"],
                    job_text=job_input["text"],
                    job_url=job_input["source_url"],
                    user_notes=user_notes,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Generation failed: {exc}")
                return

        generation = persist_generation(
            storage_config,
            {
                "resume_name": selected_resume["name"],
                "job_title": result.get("role_title", job_input["title"]),
                "company_name": result.get("company_name", "Hiring Team"),
                "source_url": job_input["source_url"],
                "fit_summary": result.get("fit_summary", ""),
                "keyword_matches": result.get("keyword_matches", []),
                "tailored_resume_content": result.get("tailored_resume_content", ""),
                "output_format": result.get("output_format", "markdown"),
                "cover_letter": result.get("cover_letter", ""),
                "cold_email": result.get("cold_email", ""),
            }
        )
        st.session_state["latest_generation"] = generation

    latest = st.session_state.get("latest_generation")
    if latest:
        render_generation_output(latest, storage_config)


def render_generation_output(generation: dict[str, object], storage_config: dict[str, str]) -> None:
    st.divider()
    st.subheader("Generated Pack")
    st.write(f"**Company:** {generation['company_name']}")
    st.write(f"**Role:** {generation['job_title']}")
    if generation.get("source_url"):
        st.write(f"**Source:** {generation['source_url']}")
    if generation.get("fit_summary"):
        st.info(str(generation["fit_summary"]))
    if generation.get("keyword_matches"):
        st.caption("Matched keywords: " + ", ".join(generation["keyword_matches"]))

    resume_content = str(generation["tailored_resume_content"])
    cover_letter = str(generation["cover_letter"])
    cold_email = str(generation["cold_email"])
    resume_format = str(generation.get("output_format", "markdown"))
    slug = _slugify(f"{generation['company_name']}-{generation['job_title']}")
    compile_key = f"{slug}-{generation.get('created_at', 'latest')}"
    compiled_pdf = _ensure_compiled_pdf(compile_key, resume_format, resume_content)

    st.markdown("#### Export Pack")
    export_format = st.radio(
        "Choose pack format",
        options=_export_options(resume_format, compiled_pdf is not None),
        horizontal=True,
        format_func=lambda value: {
            "pdf": "PDF",
            "docx": "DOCX",
            "md": "MD",
            "latex-source": "TEX + Text",
            "compiled-pdf": "Compiled PDF Pack",
        }[value],
    )
    pack_files = _bundle_files(
        slug,
        export_format,
        resume_content,
        cover_letter,
        cold_email,
        resume_format=resume_format,
        compiled_resume_pdf=compiled_pdf,
    )
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        st.download_button(
            f"Download all 3 ({export_format.upper()} ZIP)",
            data=zip_bytes(pack_files),
            file_name=f"{slug}-{export_format}-pack.zip",
            mime="application/zip",
        )
    with action_col2:
        if st.button(f"Save all 3 to GitHub ({export_format.upper()})", type="secondary"):
            folder = f"exports/{slug}-{generation['created_at'].replace(':', '-').replace('T', '_').replace('Z', '')}"
            saved_paths = persist_export_bundle(storage_config, folder, pack_files)
            st.success("Saved pack to GitHub:\n" + "\n".join(saved_paths))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Tailored Resume")
        if resume_format == "latex":
            st.text_area("Tailored LaTeX", value=resume_content, height=320)
            st.download_button(
                "Download resume (.tex)",
                data=resume_content.encode("utf-8"),
                file_name=f"{slug}-resume.tex",
                mime="application/x-tex",
            )
            if compiled_pdf is not None:
                st.download_button(
                    "Download compiled resume (.pdf)",
                    data=compiled_pdf,
                    file_name=f"{slug}-resume.pdf",
                    mime="application/pdf",
                )
                components.html(pdf_preview_iframe(compiled_pdf, height=520), height=540)
            elif latex_compiler_available():
                st.warning("The LaTeX compiler is available, but this file did not compile successfully.")
                st.code(st.session_state.get(f"{compile_key}-compile-error", "Compilation failed."), language="text")
            else:
                st.info("LaTeX preview will appear when the app is running in an environment with `latexmk`, `pdflatex`, or `xelatex`.")
        else:
            st.text_area("Tailored resume output", value=resume_content, height=320)
            st.download_button(
                "Download resume (.md)",
                data=markdown_bytes(resume_content),
                file_name=f"{slug}-resume.md",
                mime="text/markdown",
            )
            st.download_button(
                "Download resume (.docx)",
                data=docx_bytes("Tailored Resume", resume_content),
                file_name=f"{slug}-resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            st.download_button(
                "Download resume (.pdf)",
                data=pdf_bytes("Tailored Resume", resume_content),
                file_name=f"{slug}-resume.pdf",
                mime="application/pdf",
            )

    with col2:
        st.markdown("#### Cover Letter")
        st.text_area("Cover letter output", value=cover_letter, height=320)
        st.download_button(
            "Download cover letter (.md)",
            data=markdown_bytes(cover_letter),
            file_name=f"{slug}-cover-letter.md",
            mime="text/markdown",
        )
        st.download_button(
            "Download cover letter (.docx)",
            data=docx_bytes("Cover Letter", cover_letter),
            file_name=f"{slug}-cover-letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        st.download_button(
            "Download cover letter (.pdf)",
            data=pdf_bytes("Cover Letter", cover_letter),
            file_name=f"{slug}-cover-letter.pdf",
            mime="application/pdf",
        )

    with col3:
        st.markdown("#### Cold Email")
        st.text_area("Cold email output", value=cold_email, height=320)
        st.download_button(
            "Download cold email (.md)",
            data=markdown_bytes(cold_email),
            file_name=f"{slug}-cold-email.md",
            mime="text/markdown",
        )
        st.download_button(
            "Download cold email (.docx)",
            data=docx_bytes("Cold Email", cold_email),
            file_name=f"{slug}-cold-email.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        st.download_button(
            "Download cold email (.pdf)",
            data=pdf_bytes("Cold Email", cold_email),
            file_name=f"{slug}-cold-email.pdf",
            mime="application/pdf",
        )


def render_history(storage_config: dict[str, str]) -> None:
    history = load_generations(storage_config)
    if not history:
        st.info("No generations yet.")
        return

    for item in history:
        with st.expander(f"{item['company_name']} | {item['job_title']} | {item['created_at']}"):
            st.write(f"Base resume: {item['resume_name']}")
            if item.get("source_url"):
                st.write(item["source_url"])
            if item.get("fit_summary"):
                st.caption(item["fit_summary"])


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "application-pack"


def _secret(key: str, default: str = "") -> str:
    env_value = os.environ.get(key)
    if env_value is not None and env_value != "":
        return env_value
    try:
        return str(st.secrets.get(key, default))
    except Exception:  # noqa: BLE001
        return default


def _bundle_files(
    slug: str,
    export_format: str,
    resume_content: str,
    cover_letter: str,
    cold_email: str,
    resume_format: str = "markdown",
    compiled_resume_pdf: bytes | None = None,
) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    if resume_format == "latex":
        if export_format == "compiled-pdf":
            if compiled_resume_pdf is None:
                raise RuntimeError("Compiled PDF is not available for this resume yet.")
            files.extend(
                [
                    (f"{slug}-resume.pdf", compiled_resume_pdf),
                    (f"{slug}-cover-letter.pdf", pdf_bytes("Cover Letter", cover_letter)),
                    (f"{slug}-cold-email.pdf", pdf_bytes("Cold Email", cold_email)),
                ]
            )
        else:
            files.extend(
                [
                    (f"{slug}-resume.tex", resume_content.encode("utf-8")),
                    (f"{slug}-cover-letter.md", markdown_bytes(cover_letter)),
                    (f"{slug}-cold-email.md", markdown_bytes(cold_email)),
                ]
            )
        return files

    documents = [
        ("resume", "Tailored Resume", resume_content),
        ("cover-letter", "Cover Letter", cover_letter),
        ("cold-email", "Cold Email", cold_email),
    ]
    for name, title, body in documents:
        if export_format == "pdf":
            files.append((f"{slug}-{name}.pdf", pdf_bytes(title, body)))
        elif export_format == "docx":
            files.append((f"{slug}-{name}.docx", docx_bytes(title, body)))
        else:
            files.append((f"{slug}-{name}.md", markdown_bytes(body)))
    return files


def _ensure_compiled_pdf(cache_key: str, resume_format: str, resume_content: str) -> bytes | None:
    if resume_format != "latex" or not latex_compiler_available():
        return None
    pdf_key = f"{cache_key}-compiled-pdf"
    error_key = f"{cache_key}-compile-error"
    if pdf_key in st.session_state:
        return st.session_state[pdf_key]
    try:
        compiled_pdf, _ = compile_latex_source(resume_content, jobname="resume")
        st.session_state[pdf_key] = compiled_pdf
        st.session_state.pop(error_key, None)
        return compiled_pdf
    except Exception as exc:  # noqa: BLE001
        st.session_state[error_key] = str(exc)
        return None


def _export_options(resume_format: str, has_compiled_pdf: bool) -> list[str]:
    if resume_format == "latex":
        options = ["latex-source"]
        if has_compiled_pdf:
            options.insert(0, "compiled-pdf")
        return options
    return ["pdf", "docx", "md"]


if __name__ == "__main__":
    main()
