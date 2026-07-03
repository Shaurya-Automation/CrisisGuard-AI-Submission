# CrisisGuard-AI — GitHub Setup

Run these from inside the project folder (the one containing `app.py`,
`agents.py`, etc.). Assumes Git is already installed and you're logged
into GitHub (via `gh auth login` or an existing credential helper).

## Option A — using GitHub CLI (`gh`)

```bash
git init
git add .
git commit -m "Initial commit: CrisisGuard-AI multi-agent capstone"
gh repo create CrisisGuard-AI-Submission --public --source=. --push
```

## Option B — plain Git (no `gh` CLI)

```bash
git init
git add .
git commit -m "Initial commit: CrisisGuard-AI multi-agent capstone"
```

Then create an empty repo named `CrisisGuard-AI-Submission` on
github.com (no README/gitignore — keep it empty), and:

```bash
git remote add origin https://github.com/<your-username>/CrisisGuard-AI-Submission.git
git branch -M main
git push -u origin main
```

## Before you push — quick checklist

- [ ] `.gitignore` excludes `context.db`, `__pycache__/`, `.pytest_cache/`
- [ ] No API keys or secrets committed anywhere (this project doesn't
      require any, by design)
- [ ] `requirements.txt` is present at the repo root
- [ ] `app.py` is at the repo root, not inside a `src/` folder
