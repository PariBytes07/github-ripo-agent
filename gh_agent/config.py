from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    github_token: str
    github_repo: str  # "owner/name"
    llm_provider: str
    llm_model: str

def load_config() -> AppConfig:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPO", "").strip()
    provider = os.environ.get("LLM_PROVIDER", "mock").strip()
    model = os.environ.get("LLM_MODEL", "mock-structured").strip()
    if not repo:
        raise SystemExit("Missing GITHUB_REPO env var (format: owner/repo).")
    # token is required only for GitHub fetch/create. Review-only can work without it.
    return AppConfig(github_token=token, github_repo=repo, llm_provider=provider, llm_model=model)
