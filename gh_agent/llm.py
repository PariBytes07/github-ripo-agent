from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
from .schemas import ReviewReport, EvidenceItem, IssueDraft, PRDraft, PlanArtifact, ReflectionArtifact

@dataclass(frozen=True)
class LLM:
    provider: str = "mock"
    model: str = "mock-structured"

    # Intentionally non-hallucinating:
    # only uses passed-in tool outputs; no invented facts.
    def classify_change(self, diff_text: str) -> str:
        d = diff_text.lower()
        if "fix" in d or "bug" in d:
            return "bugfix"
        if "refactor" in d:
            return "refactor"
        if "readme" in d or "docs" in d:
            return "docs"
        if "test" in d:
            return "chore"
        if diff_text.strip():
            return "feature"
        return "unknown"

    def risk_from_diff(self, diff_text: str) -> str:
        lines = diff_text.splitlines()
        add = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
        rem = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
        touched_sensitive = any(
            k in diff_text.lower()
            for k in ["auth", "login", "payment", "billing", "crypto", "encryption", "permission", "rbac", "sql", "migrate"]
        )
        if touched_sensitive and (add + rem) > 30:
            return "high"
        if (add + rem) > 200:
            return "high"
        if (add + rem) > 60:
            return "medium"
        return "low"

    def make_plan(self, goal: str, inputs: List[str]) -> PlanArtifact:
        return PlanArtifact(
            goal=goal,
            inputs=inputs,
            steps=[
                "Inspect grounded evidence (diff, changed files, relevant file excerpts).",
                "List concrete issues/improvements with file-level evidence.",
                "Decide action (issue/pr/no action) based on severity and scope.",
                "If drafting: generate structured draft with explicit acceptance criteria and test plan.",
                "Run Critic reflection to ensure no unsupported claims and required fields present.",
            ],
            success_criteria=[
                "Every issue/improvement has at least one evidence snippet.",
                "Decision matches evidence and risk assessment.",
                "Draft includes all required sections.",
                "Reflection verdict PASS before any GitHub creation.",
            ],
        )

    def review(self, diff_text: str, changed_files: List[str]) -> ReviewReport:
        change_type = self.classify_change(diff_text)
        risk = self.risk_from_diff(diff_text)
        issues = []
        improvements = []

        if "TODO" in diff_text:
            issues.append("TODO left in code changes.")
        if "print(" in diff_text or "console.log" in diff_text.lower():
            improvements.append("Potential debug logging added; confirm it should remain.")
        if "+except:" in diff_text or "+except Exception" in diff_text:
            improvements.append("Exception handling may be broad; consider narrowing exception types.")

        # Default decision rule (grounded)
        if issues:
            decision = "create_issue"
        elif risk in ("high", "medium") and diff_text.strip():
            decision = "create_pr"
        else:
            decision = "no_action"

        excerpt = "\n".join(diff_text.splitlines()[:40])
        ev = [EvidenceItem(file=(changed_files[0] if changed_files else "(diff)"), snippet=excerpt or "(empty diff)")]
        return ReviewReport(
            change_type=change_type,
            risk=risk,
            decision=decision,
            issues_found=issues,
            improvements=improvements,
            evidence=ev,
        )

    def draft_issue(self, instruction: str, evidence: List[str], risk: str) -> IssueDraft:
        title = instruction.strip().rstrip(".")
        if len(title) > 80:
            title = title[:77] + "..."
        return IssueDraft(
            title=title,
            problem_description=instruction,
            evidence=evidence or ["(No evidence provided yet — attach diff/file excerpts.)"],
            acceptance_criteria=[
                "Add validation/handling that prevents the reported failure mode.",
                "Add/adjust tests to cover the new behavior.",
                "Confirm no regressions in related flows.",
            ],
            risk_level=risk,
        )

    def draft_pr(self, instruction: str, files: List[str], risk: str) -> PRDraft:
        title = instruction.strip().rstrip(".")
        if len(title) > 80:
            title = title[:77] + "..."
        return PRDraft(
            title=title,
            summary=instruction,
            files_affected=files,
            behavior_change="Describe externally observable behavior changes (or state 'No user-facing changes').",
            test_plan=[
                "Run existing unit/integration tests.",
                "Add new tests for changed logic.",
                "Manual sanity check for the modified flow (if applicable).",
            ],
            risk_level=risk,
        )

    def reflect_on_draft(self, draft: Dict[str, Any], required_fields: List[str]) -> ReflectionArtifact:
        missing = [f for f in required_fields if f not in draft or not draft.get(f)]
        reasons = []
        unsupported = []
        missing_evidence = []
        missing_tests = []
        policy = []

        if missing:
            reasons.append(f"Missing required fields: {', '.join(missing)}")

        if "test_plan" in required_fields and not draft.get("test_plan"):
            missing_tests.append("PR draft missing test plan.")

        if "evidence" in required_fields and (
            not draft.get("evidence") or any("No evidence" in str(x) for x in draft.get("evidence", []))
        ):
            missing_evidence.append("Evidence is missing or placeholder.")

        verdict = "FAIL" if (missing or missing_evidence or missing_tests or policy) else "PASS"
        if verdict == "PASS":
            reasons.append("All required fields present; no placeholder evidence/tests detected.")
        return ReflectionArtifact(
            verdict=verdict,
            reasons=reasons,
            unsupported_claims=unsupported,
            missing_evidence=missing_evidence,
            missing_tests=missing_tests,
            policy_violations=policy,
        )
