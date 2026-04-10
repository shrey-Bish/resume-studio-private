from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from resume_studio.ai_client import generate_application_pack
from resume_studio.exporters import docx_bytes, markdown_bytes, pdf_bytes, pdf_export_supported
from resume_studio.job_parser import build_job_input, extract_resume_text
from resume_studio.storage import (
    load_generations,
    load_resumes,
    persist_generation,
    persist_resume,
    seed_resume_if_missing_remote,
)
DEFAULT_CV_PATH = ROOT_DIR / "cv.md"


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
    api_key = _secret("GEMINI_API_KEY").strip()

    with st.sidebar:
        st.subheader("Workspace")
        st.caption(f"GitHub storage: `{storage_config['repo']}`")
        st.caption(f"Branch: `{storage_config['branch']}`")

        model = st.selectbox(
            "Model",
            options=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
            index=0,
        )

        st.subheader("Tips")
        st.markdown(
            "- Upload your 3 base resumes first.\n"
            "- Paste either a JD, a link, or both.\n"
            "- Add notes like tone, visa mention, or preferred project emphasis."
        )
        if not pdf_export_supported():
            st.caption("PDF export is disabled here, so use Markdown or DOCX downloads.")

    if not storage_config["repo"] or not storage_config["token"]:
        st.error("GitHub storage is required. Add `GITHUB_REPO` and `GITHUB_TOKEN` to Streamlit secrets.")
        return

    if not api_key:
        st.error("Add `GEMINI_API_KEY` to Streamlit secrets to generate tailored documents.")
        return

    if DEFAULT_CV_PATH.exists():
        seed_resume_if_missing_remote(
            storage_config=storage_config,
            name="Imported from cv.md",
            source_filename="cv.md",
            text=DEFAULT_CV_PATH.read_text(encoding="utf-8"),
        )

    tab_library, tab_generate, tab_history = st.tabs(["Resume Library", "Tailor for a Job", "Recent Generations"])

    with tab_library:
        render_resume_library(storage_config)

    with tab_generate:
        render_generation_tab(api_key=api_key, model=model, storage_config=storage_config)

    with tab_history:
        render_history(storage_config)


def render_resume_library(storage_config: dict[str, str]) -> None:
    st.subheader("Base Resume Library")
    uploads = st.file_uploader(
        "Upload resumes",
        type=["pdf", "docx", "doc", "txt", "md"],
        accept_multiple_files=True,
        help="Recommended names: AI+SE, SE, and DE.",
    )

    if uploads:
        for upload in uploads:
            extracted_text = extract_resume_text(upload.name, upload.getvalue())
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
                    persist_resume(storage_config, custom_name, upload.name, extracted_text)
                    st.success(f"Saved {custom_name}")
                    st.rerun()

    resumes = load_resumes(storage_config)
    if not resumes:
        st.info("No resumes saved yet. Upload your base resumes to get started.")
        return

    for resume in resumes:
        with st.expander(f"{resume['name']}  |  {resume['source_filename']}"):
            st.caption(f"Updated: {resume['updated_at']}")
            st.text_area(
                "Resume text",
                value=resume["text"],
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
            st.error("Add your OpenAI API key in the sidebar first.")
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
                    resume_text=selected_resume["text"],
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
                "tailored_resume_markdown": result.get("tailored_resume_markdown", ""),
                "cover_letter": result.get("cover_letter", ""),
                "cold_email": result.get("cold_email", ""),
            }
        )
        st.session_state["latest_generation"] = generation

    latest = st.session_state.get("latest_generation")
    if latest:
        render_generation_output(latest)


def render_generation_output(generation: dict[str, object]) -> None:
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

    resume_md = str(generation["tailored_resume_markdown"])
    cover_letter = str(generation["cover_letter"])
    cold_email = str(generation["cold_email"])
    slug = _slugify(f"{generation['company_name']}-{generation['job_title']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Tailored Resume")
        st.text_area("Tailored resume output", value=resume_md, height=320)
        st.download_button(
            "Download resume (.md)",
            data=markdown_bytes(resume_md),
            file_name=f"{slug}-resume.md",
            mime="text/markdown",
        )
        st.download_button(
            "Download resume (.docx)",
            data=docx_bytes("Tailored Resume", resume_md),
            file_name=f"{slug}-resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        if pdf_export_supported():
            st.download_button(
                "Download resume (.pdf)",
                data=pdf_bytes("Tailored Resume", resume_md),
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
        if pdf_export_supported():
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
        if pdf_export_supported():
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
    try:
        return str(st.secrets.get(key, default))
    except Exception:  # noqa: BLE001
        return default


if __name__ == "__main__":
    main()
