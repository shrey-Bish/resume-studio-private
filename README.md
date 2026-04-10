# Resume Studio Private

Resume Studio is a Streamlit app that helps tailor one of your base resumes to a job description and generate:

- a tailored resume
- a brief cover letter
- a cold outreach email

It supports:

- multiple uploaded resume variants
- JD text paste or job URL scraping
- PDF, DOCX, and Markdown downloads
- optional GitHub-backed storage in a private repo

## Run locally

```bash
cd /Users/shrey/Downloads/Resume/career-ops
python3 -m venv .venv-resume-studio
source .venv-resume-studio/bin/activate
pip install -r requirements-resume-studio.txt
npm install
streamlit run resume_studio/app.py
```

`npm install` is needed for the Playwright-based PDF renderer and browser fallback scraper.

## Storage modes

- `Local files`: stores data in `resume_studio/data/`
- `GitHub private repo`: stores resume and generation JSON in your private repo using a GitHub token

## GitHub Pages

This repo includes a static landing page in `docs/` that can be served with GitHub Pages.

The full Streamlit app itself cannot run on GitHub Pages because it needs a Python backend. GitHub Pages can host the project page and instructions, but the app should be run locally or deployed on a Python host like Streamlit Community Cloud, Render, or Railway.

