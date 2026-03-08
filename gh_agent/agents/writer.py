from __future__ import annotations
from dataclasses import dataclass
from ..llm import LLM
from ..schemas import IssueDraft, PRDraft, ReviewReport

@dataclass
class WriterAgent:
    llm: LLM

    def draft_issue(self, instruction: str, evidence: list[str], risk: str) -> IssueDraft:
        return self.llm.draft_issue(instruction=instruction, evidence=evidence, risk=risk)

    def draft_pr(self, instruction: str, files: list[str], risk: str) -> PRDraft:
        return self.llm.draft_pr(instruction=instruction, files=files, risk=risk)

    def draft_from_review(self, review: ReviewReport, changed_files: list[str]) -> IssueDraft | PRDraft:
        ev = [e.snippet for e in review.evidence]
        if review.decision == "create_issue":
            instruction = "Create an issue based on review findings."
            return self.draft_issue(instruction=instruction, evidence=ev, risk=review.risk)
        if review.decision == "create_pr":
            instruction = "Create a PR based on reviewed changes."
            return self.draft_pr(instruction=instruction, files=changed_files, risk=review.risk)
        instruction = "No action required per review; drafting informational issue."
        return self.draft_issue(instruction=instruction, evidence=ev, risk=review.risk)
