from __future__ import annotations
import subprocess
from dataclasses import dataclass

@dataclass(frozen=True)
class GitDiffResult:
    command: str
    diff_text: str

def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout

def git_diff_base(base_branch: str) -> GitDiffResult:
    # diff from merge-base to HEAD
    base = _run(["git", "merge-base", base_branch, "HEAD"]).strip()
    diff = _run(["git", "diff", f"{base}..HEAD"])
    return GitDiffResult(command=f"git diff {base}..HEAD", diff_text=diff)

def git_diff_range(commit_range: str) -> GitDiffResult:
    diff = _run(["git", "diff", commit_range])
    return GitDiffResult(command=f"git diff {commit_range}", diff_text=diff)

def git_changed_files_from_diff(diff_text: str) -> list[str]:
    files: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                b = parts[3]  # b/path
                if b.startswith("b/"):
                    files.append(b[2:])
    # preserve order, unique
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out

def git_current_branch() -> str:
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()

def git_root() -> str:
    return _run(["git", "rev-parse", "--show-toplevel"]).strip()
