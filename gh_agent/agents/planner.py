from __future__ import annotations
from dataclasses import dataclass
from ..llm import LLM
from ..schemas import PlanArtifact, ReviewReport

@dataclass
class PlannerAgent:
    llm: LLM

    def run(self, review: ReviewReport, inputs: list[str]) -> PlanArtifact:
        goal = f"Decide next action based on review decision={review.decision}, risk={review.risk}"
        return self.llm.make_plan(goal=goal, inputs=inputs)
