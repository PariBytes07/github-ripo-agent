# GitHub Repository Agent (CLI)

This project implements a personalized AI agent that can:
- Review local git changes (diff-based, evidence grounded)
- Draft Issues/PRs with human approval required before GitHub creation
- Improve existing Issues/PRs (critique first, then structured rewrite)

## Requirements
- Python 3.10+
- A git repository (run inside your repo)
- GitHub token for creation/fetch:
  - `export GITHUB_TOKEN="..."`
  - `export GITHUB_REPO="owner/repo"`  (e.g., octocat/Hello-World)

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Commands

### Review
```bash
gh_agent review --base main
gh_agent review --range HEAD~3..HEAD
```

### Draft from instruction
```bash
gh_agent draft issue --instruction "Add rate limiting to login endpoint"
gh_agent draft pr --instruction "Refactor duplicated pricing logic"
```

### Draft from last review
```bash
gh_agent draft from-review
```

### Approve/Reject
```bash
gh_agent approve --yes
gh_agent approve --no
```

### Improve existing
```bash
gh_agent improve issue --number 42
gh_agent improve pr --number 17
```



