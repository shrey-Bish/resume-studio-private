# Resume Studio

Resume Studio is a Streamlit app for managing multiple base resumes and tailoring them per job description.

## Features

- Upload and store multiple resumes locally
- Paste a JD, a job link, or both
- Choose which base resume to tailor
- Generate:
  - tailored resume
  - brief cover letter
  - cold outreach email
- Download outputs as `.md` or `.docx`
- Download outputs as `.md`, `.docx`, or `.pdf`
- Keep a small local history of recent generations
- Optionally store resumes and generation history in a private GitHub repo

## Run

```bash
cd /Users/shrey/Downloads/Resume/career-ops
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-resume-studio.txt
streamlit run resume_studio/app.py
```

Then open the local Streamlit URL in your browser, add your OpenAI API key in the sidebar, and start uploading resumes.

## Notes

- The app seeds one resume automatically from `cv.md` if that file exists.
- Resume and generation data stay local in `resume_studio/data/`.
- You can switch storage to GitHub in the sidebar and save data into a private repo using a fine-grained GitHub token.
- Job links first use a regular HTTP scrape, then fall back to a headless browser render for JS-heavy pages.
- Review generated content before sending it anywhere.
