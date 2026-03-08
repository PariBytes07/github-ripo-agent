from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, List

Risk = Literal["low", "medium", "high"]
ChangeType = Literal["feature", "bugfix", "refactor", "docs", "chore", "unknown"]
Decision = Literal["create_issue", "create_pr", "no_action"]

class EvidenceItem(BaseModel):
    file: str
    snippet: str = Field(..., description="A short excerpt from diff or file read that supports the claim.")

class ReviewReport(BaseModel):
    change_type: ChangeType
    risk: Risk
    decision: Decision
    issues_found: List[str]
    improvements: List[str]
    evidence: List[EvidenceItem]

class PlanArtifact(BaseModel):
    goal: str
    inputs: List[str]
    steps: List[str]
    success_criteria: List[str]

class IssueDraft(BaseModel):
    title: str
    problem_description: str
    evidence: List[str]
    acceptance_criteria: List[str]
    risk_level: Risk

class PRDraft(BaseModel):
    title: str
    summary: str
    files_affected: List[str]
    behavior_change: str
    test_plan: List[str]
    risk_level: Risk

class ReflectionArtifact(BaseModel):
    verdict: Literal["PASS", "FAIL"]
    reasons: List[str]
    unsupported_claims: List[str]
    missing_evidence: List[str]
    missing_tests: List[str]
    policy_violations: List[str]
