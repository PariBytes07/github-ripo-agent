from __future__ import annotations
import requests
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class GitHubClient:
    token: str
    repo: str  # "owner/name"

    @property
    def _base(self) -> str:
        return f"https://api.github.com/repos/{self.repo}"

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get_issue(self, number: int) -> Dict[str, Any]:
        r = requests.get(f"{self._base}/issues/{number}", headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def get_pr(self, number: int) -> Dict[str, Any]:
        r = requests.get(f"{self._base}/pulls/{number}", headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def create_issue(self, title: str, body: str) -> Dict[str, Any]:
        r = requests.post(
            f"{self._base}/issues",
            headers=self._headers(),
            json={"title": title, "body": body},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def create_pr(self, title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        r = requests.post(
            f"{self._base}/pulls",
            headers=self._headers(),
            json={"title": title, "body": body, "head": head, "base": base},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
