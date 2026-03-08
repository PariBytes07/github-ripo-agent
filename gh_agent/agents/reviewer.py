from __future__ import annotations
from dataclasses import dataclass
from ..llm import LLM
from ..schemas import ReviewReport

@dataclass
class ReviewerAgent:
    llm: LLM

    def run(self, diff_text: str, changed_files: list[str]) -> ReviewReport:
        return self.llm.review(diff_text=diff_text, changed_files=changed_files)
