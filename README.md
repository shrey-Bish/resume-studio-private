# Resume Studio Private

Resume Studio is a Streamlit app that helps tailor one of your base resumes to a job description and generate:

- a tailored resume
- a brief cover letter
- a cold outreach email

It supports:

- multiple uploaded resume variants
- LaTeX resume upload and tailoring
- real PDF preview for tailored LaTeX resumes when a TeX compiler is available
- JD text paste or job URL scraping
- PDF, DOCX, and Markdown downloads
- optional GitHub-backed storage in a private repo
- GitHub-backed storage enabled by default
- export all 3 generated documents together as a ZIP and save the pack back to GitHub
- Render-first deployment path with Docker
- system packages installed for future LaTeX-based resume workflows

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

## Deploy on Render

This repo now includes:

- `Dockerfile` for a containerized Render deploy
- `render.yaml` as a Render Blueprint
- TeX packages in the image so you can grow into a LaTeX compile flow

### Render setup

1. Push this repo to GitHub.
2. In Render, create a new `Blueprint` or `Web Service` from the repo.
3. If using a Web Service manually, choose `Docker`.
4. Add environment variables from `.streamlit/secrets.toml.example`.

Required env vars:

- `GROQ_API_KEY`
- `GITHUB_REPO`
- `GITHUB_BRANCH`
- `GITHUB_TOKEN`

Render will expose a `PORT` env var automatically, and the container is already configured to use it.

## Why Render

Render is the preferred target for the next version because it can run a normal Dockerized Python app with system packages.
That makes it a much better fit than Streamlit Community Cloud for:

- LaTeX toolchains like `pdflatex`, `xelatex`, or `latexmk`
- richer PDF pipelines
- real-time compile/preview flows for `.tex` resumes
