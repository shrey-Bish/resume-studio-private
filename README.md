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
- GitHub-backed storage enabled by default in Streamlit Cloud

## Run locally

```bash
cd /Users/shrey/Downloads/Resume/career-ops
python3 -m venv .venv-resume-studio
source .venv-resume-studio/bin/activate
pip install -r requirements-resume-studio.txt
npm install
streamlit run app.py
```

`npm install` is needed for the Playwright-based PDF renderer and browser fallback scraper.

## Storage modes

- `Local files`: stores data in `resume_studio/data/`
- `GitHub private repo`: stores resume and generation JSON in your private repo using a GitHub token

## GitHub Pages

This repo includes a static landing page in `docs/` that can be served with GitHub Pages.

The full Streamlit app itself cannot run on GitHub Pages because it needs a Python backend. GitHub Pages can host the project page and instructions, but the app should be run locally or deployed on a Python host like Streamlit Community Cloud, Render, or Railway.

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. In Streamlit Community Cloud, create a new app from `shrey-Bish/resume-studio-private`.
3. Set the main file path to `app.py`.
4. Add secrets from `.streamlit/secrets.toml.example`.

Notes:

- `requirements.txt` is included for Streamlit Cloud.
- The app reads `OPENAI_API_KEY`, `GITHUB_REPO`, `GITHUB_BRANCH`, and `GITHUB_TOKEN` from Streamlit secrets and does not ask for them in the UI.
- The app will still run if Node/Playwright is unavailable, but PDF downloads and browser-rendered JD scraping may be disabled there.
