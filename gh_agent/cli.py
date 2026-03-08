from __future__ import annotations
import typer
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

from .config import load_config
from .state_store import load_state, save_state, clear_state
from .tools_git import git_diff_base, git_diff_range, git_changed_files_from_diff, git_current_branch
from .tools_github import GitHubClient
from .llm import LLM
from .agents.reviewer import ReviewerAgent
from .agents.planner import PlannerAgent
from .agents.writer import WriterAgent
from .agents.gatekeeper import GatekeeperAgent

app = typer.Typer(no_args_is_help=True)
draft_app = typer.Typer(no_args_is_help=True)
improve_app = typer.Typer(no_args_is_help=True)
app.add_typer(draft_app, name="draft")
app.add_typer(improve_app, name="improve")

console = Console()

def _print_artifact(title: str, obj) -> None:
    console.print(Panel.fit(Pretty(obj), title=title))

@app.command()
def review(
    base: str = typer.Option(None, "--base", help="Base branch to diff against (uses merge-base)."),
    range: str = typer.Option(None, "--range", help="Commit range like HEAD~3..HEAD."),
):
    """
    Task 1: Review changes (diff-grounded). Produces Reviewer + Planner artifacts and stores them as last_review.
    """
    cfg = load_config()
    llm = LLM(provider=cfg.llm_provider, model=cfg.llm_model)

    if bool(base) == bool(range):
        raise typer.BadParameter("Provide exactly one of --base or --range.")

    diff_res = git_diff_base(base) if base else git_diff_range(range)
    changed_files = git_changed_files_from_diff(diff_res.diff_text)

    reviewer = ReviewerAgent(llm=llm)
    planner = PlannerAgent(llm=llm)

    review_report = reviewer.run(diff_text=diff_res.diff_text, changed_files=changed_files)
    plan = planner.run(review=review_report, inputs=[diff_res.command, f"changed_files={changed_files}"])

    console.print(f"[bold][Reviewer][/bold] Analyzed: {diff_res.command}")
    _print_artifact("ReviewReport", review_report.model_dump())
    console.print(f"[bold][Planner][/bold] Plan produced.")
    _print_artifact("PlanArtifact", plan.model_dump())

    state = load_state()
    state["last_review"] = {
        "diff_command": diff_res.command,
        "changed_files": changed_files,
        "review_report": review_report.model_dump(),
        "plan": plan.model_dump(),
    }
    save_state(state)
    console.print("[green]Saved last_review to .gh_agent_state.json[/green]")

@draft_app.command("issue")
def draft_issue(instruction: str = typer.Option(..., "--instruction")):
    """
    Task 2: Draft an Issue from explicit instruction.
    """
    cfg = load_config()
    llm = LLM(provider=cfg.llm_provider, model=cfg.llm_model)
    writer = WriterAgent(llm=llm)
    gatekeeper = GatekeeperAgent(llm=llm)

    draft = writer.draft_issue(instruction=instruction, evidence=[], risk="medium")
    reflection = gatekeeper.reflect_issue(draft.model_dump())

    console.print("[bold][Writer][/bold] Draft Issue created.")
    _print_artifact("IssueDraft", draft.model_dump())
    console.print("[bold][Gatekeeper][/bold] Reflection artifact produced.")
    _print_artifact("ReflectionArtifact", reflection.model_dump())

    state = load_state()
    state["pending_draft"] = {
        "type": "issue",
        "draft": draft.model_dump(),
        "reflection": reflection.model_dump(),
    }
    save_state(state)
    console.print("[yellow]Pending draft saved. Run `gh_agent approve --yes|--no`.[/yellow]")

@draft_app.command("pr")
def draft_pr(instruction: str = typer.Option(..., "--instruction")):
    """
    Task 2: Draft a PR from explicit instruction.
    """
    cfg = load_config()
    llm = LLM(provider=cfg.llm_provider, model=cfg.llm_model)
    writer = WriterAgent(llm=llm)
    gatekeeper = GatekeeperAgent(llm=llm)

    draft = writer.draft_pr(instruction=instruction, files=[], risk="medium")
    reflection = gatekeeper.reflect_pr(draft.model_dump())

    console.print("[bold][Writer][/bold] Draft PR created.")
    _print_artifact("PRDraft", draft.model_dump())
    console.print("[bold][Gatekeeper][/bold] Reflection artifact produced.")
    _print_artifact("ReflectionArtifact", reflection.model_dump())

    state = load_state()
    state["pending_draft"] = {
        "type": "pr",
        "draft": draft.model_dump(),
        "reflection": reflection.model_dump(),
    }
    save_state(state)
    console.print("[yellow]Pending draft saved. Run `gh_agent approve --yes|--no`.[/yellow]")

@draft_app.command("from-review")
def draft_from_review():
    """
    Task 2: Draft Issue/PR from the last review (grounded in diff evidence).
    """
    cfg = load_config()
    llm = LLM(provider=cfg.llm_provider, model=cfg.llm_model)
    writer = WriterAgent(llm=llm)
    gatekeeper = GatekeeperAgent(llm=llm)

    state = load_state()
    if "last_review" not in state:
        raise SystemExit("No last_review found. Run `gh_agent review ...` first.")

    rr = state["last_review"]["review_report"]
    changed_files = state["last_review"]["changed_files"]
    decision = rr["decision"]

    from .schemas import ReviewReport
    review_report = ReviewReport(**rr)

    draft_obj = writer.draft_from_review(review=review_report, changed_files=changed_files)
    draft_dict = draft_obj.model_dump()

    if decision == "create_pr":
        reflection = gatekeeper.reflect_pr(draft_dict)
        draft_type = "pr"
    else:
        reflection = gatekeeper.reflect_issue(draft_dict)
        draft_type = "issue"

    console.print(f"[bold][Writer][/bold] Draft created from review decision={decision}.")
    _print_artifact("Draft", draft_dict)
    console.print("[bold][Gatekeeper][/bold] Reflection artifact produced.")
    _print_artifact("ReflectionArtifact", reflection.model_dump())

    state["pending_draft"] = {
        "type": draft_type,
        "draft": draft_dict,
        "reflection": reflection.model_dump(),
        "source": "from-review",
    }
    save_state(state)
    console.print("[yellow]Pending draft saved. Run `gh_agent approve --yes|--no`.[/yellow]")

@app.command()
def approve(
    yes: bool = typer.Option(False, "--yes", help="Approve and create on GitHub."),
    no: bool = typer.Option(False, "--no", help="Reject and abort safely."),
    base: str = typer.Option("main", "--base", help="Base branch for PR creation."),
    head: str = typer.Option(None, "--head", help="Head branch for PR creation (defaults to current branch)."),
):
    """
    Human approval gate. If approved and reflection PASS, create Issue/PR via GitHub API.
    """
    if yes == no:
        raise typer.BadParameter("Provide exactly one of --yes or --no.")

    state = load_state()
    if "pending_draft" not in state:
        raise SystemExit("No pending draft found. Run `gh_agent draft ...` first.")

    if no:
        console.print("[bold][Gatekeeper][/bold] Draft rejected. No changes made.")
        clear_state()
        return

    pending = state["pending_draft"]
    draft_type = pending["type"]
    draft = pending["draft"]
    reflection = pending["reflection"]

    if reflection["verdict"] != "PASS":
        console.print("[red][Gatekeeper][/red] Reflection verdict: FAIL — creation blocked.")
        _print_artifact("ReflectionArtifact", reflection)
        raise SystemExit("Revise draft (or re-run from-review) until reflection PASS.")

    cfg = load_config()
    if not cfg.github_token:
        raise SystemExit("Missing GITHUB_TOKEN env var required to create Issue/PR on GitHub.")

    gh = GitHubClient(token=cfg.github_token, repo=cfg.github_repo)

    if draft_type == "issue":
        title = draft["title"]
        body = _format_issue_body(draft)
        console.print("[bold][Gatekeeper][/bold] Creating GitHub Issue...")
        created = gh.create_issue(title=title, body=body)
        console.print(f"[green]Created Issue #{created.get('number')}[/green]")
        _print_artifact("GitHubResponse", {"url": created.get("html_url"), "number": created.get("number")})
    else:
        title = draft["title"]
        body = _format_pr_body(draft)
        if not head:
            head = git_current_branch()
        console.print("[bold][Gatekeeper][/bold] Creating GitHub Pull Request...")
        created = gh.create_pr(title=title, body=body, head=head, base=base)
        console.print(f"[green]Created PR #{created.get('number')}[/green]")
        _print_artifact("GitHubResponse", {"url": created.get("html_url"), "number": created.get("number")})

    clear_state()

@improve_app.command("issue")
def improve_issue(number: int = typer.Option(..., "--number")):
    """
    Task 3: Improve an existing Issue (critique first, then structured rewrite).
    """
    cfg = load_config()
    if not cfg.github_token:
        raise SystemExit("Missing GITHUB_TOKEN env var required to fetch Issue.")
    gh = GitHubClient(token=cfg.github_token, repo=cfg.github_repo)

    issue = gh.get_issue(number)
    title = issue.get("title", "")
    body = issue.get("body", "") or ""

    critique, improved = _improve_text(kind="issue", title=title, body=body)

    console.print("[bold][Reviewer][/bold] Critique:")
    _print_artifact("Critique", critique)
    console.print("[bold][Writer][/bold] Proposed improved structured version:")
    _print_artifact("ImprovedIssue", improved)

@improve_app.command("pr")
def improve_pr(number: int = typer.Option(..., "--number")):
    """
    Task 3: Improve an existing PR (critique first, then structured rewrite).
    """
    cfg = load_config()
    if not cfg.github_token:
        raise SystemExit("Missing GITHUB_TOKEN env var required to fetch PR.")
    gh = GitHubClient(token=cfg.github_token, repo=cfg.github_repo)

    pr = gh.get_pr(number)
    title = pr.get("title", "")
    body = pr.get("body", "") or ""

    critique, improved = _improve_text(kind="pr", title=title, body=body)

    console.print("[bold][Reviewer][/bold] Critique:")
    _print_artifact("Critique", critique)
    console.print("[bold][Writer][/bold] Proposed improved structured version:")
    _print_artifact("ImprovedPR", improved)

def _format_issue_body(d: dict) -> str:
    return (
        f"## Problem\n{d['problem_description']}\n\n"
        f"## Evidence\n" + "\n".join(f"- {e}" for e in d["evidence"]) + "\n\n"
        f"## Acceptance Criteria\n" + "\n".join(f"- [ ] {a}" for a in d["acceptance_criteria"]) + "\n\n"
        f"## Risk\n**{d['risk_level']}**\n"
    )

def _format_pr_body(d: dict) -> str:
    return (
        f"## Summary\n{d['summary']}\n\n"
        f"## Files Affected\n" + "\n".join(f"- {f}" for f in d["files_affected"]) + "\n\n"
        f"## Behavior Change\n{d['behavior_change']}\n\n"
        f"## Test Plan\n" + "\n".join(f"- [ ] {t}" for t in d["test_plan"]) + "\n\n"
        f"## Risk\n**{d['risk_level']}**\n"
    )

def _improve_text(kind: str, title: str, body: str):
    critique = {
        "missing": [],
        "vagueness": [],
        "acceptance_criteria_quality": [],
        "evidence_quality": [],
    }
    if "acceptance" not in body.lower():
        critique["missing"].append("No explicit acceptance criteria section.")
    if "test" not in body.lower():
        critique["missing"].append("No test plan / verification steps mentioned.")
    if len(body.strip()) < 80:
        critique["vagueness"].append("Body is very short; likely missing context and steps to reproduce.")
    if "maybe" in body.lower() or "somehow" in body.lower():
        critique["vagueness"].append("Contains vague language ('maybe/somehow'); consider concrete statements.")

    improved = {
        "title": title.strip() or f"Improve {kind} description",
        "body": (
            "## Context\n(Explain background and why this matters.)\n\n"
            "## Problem\n(Describe the current behavior and what is wrong.)\n\n"
            "## Evidence\n- Link to relevant logs, screenshots, or code references\n"
            "- Steps to reproduce (if applicable)\n\n"
            "## Acceptance Criteria\n- [ ] Define clear expected behavior\n"
            "- [ ] Add/update tests\n"
            "- [ ] Confirm edge cases and error handling\n\n"
            "## Risk\n(low/medium/high) — justify briefly\n\n"
            "## Test Plan\n- [ ] Unit tests\n"
            "- [ ] Integration/E2E (if applicable)\n"
            "- [ ] Manual verification steps\n"
        )
    }
    return critique, improved
