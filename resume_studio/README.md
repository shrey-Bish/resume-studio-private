# Resume Studio

Resume Studio is a Streamlit app for managing multiple LaTeX base resumes and tailoring them per job description.

## Features

- Upload or paste multiple `.tex` resumes
- Paste a JD, a job link, or both
- Choose which base resume to tailor
- Auto-select relevant GitHub repos against the JD
- Generate:
  - tailored LaTeX resume
  - brief cover letter
  - cold outreach email
- Recompile edited LaTeX and preview the real PDF
- Save resumes, history, and export packs in a private GitHub repo

## Run

```bash
cd /Users/shrey/Downloads/Resume/career-ops
python3 -m venv .venv-resume-studio
source .venv-resume-studio/bin/activate
pip install -r requirements-resume-studio.txt
npm install
streamlit run resume_studio/app.py
```

Then open the local Streamlit URL in your browser and configure your secrets or environment variables.

## Notes

- The app expects GitHub-backed storage by default.
- Set `GROQ_API_KEY`, `GITHUB_REPO`, `GITHUB_BRANCH`, and `GITHUB_TOKEN`.
- Set `GITHUB_USERNAME` too if you want repo matching scoped to a specific account.
- Job links first use a regular HTTP scrape, then fall back to a headless browser render for JS-heavy pages.
- Review generated content before sending it anywhere.
