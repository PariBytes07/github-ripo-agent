from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
from ..llm import LLM
from ..schemas import ReflectionArtifact

@dataclass
class GatekeeperAgent:
    llm: LLM

    def reflect_issue(self, draft_dict: Dict[str, Any]) -> ReflectionArtifact:
        required = ["title", "problem_description", "evidence", "acceptance_criteria", "risk_level"]
        return self.llm.reflect_on_draft(draft=draft_dict, required_fields=required)

    def reflect_pr(self, draft_dict: Dict[str, Any]) -> ReflectionArtifact:
        required = ["title", "summary", "files_affected", "behavior_change", "test_plan", "risk_level"]
        return self.llm.reflect_on_draft(draft=draft_dict, required_fields=required)
