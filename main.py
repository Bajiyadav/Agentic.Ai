import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.agent_1_resume_parser import parse_resume, CandidateClaims
from src.agent_2_code_auditor import audit_github, GitHubEvidence
from src.agent_3_evaluator import evaluate_candidate, ScreeningScorecard

console = Console()

def run_screening_pipeline(
    pdf_path: str,
    github_username: Optional[str] = None,
    save_report: bool = True
) -> ScreeningScorecard:
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔍 AI RESUME & CODE EVIDENCE SCREENER[/bold cyan]\n"
        "[dim]Auditing Candidate Claims vs Actual Public GitHub Evidence[/dim]",
        border_style="cyan"
    ))
    console.print()

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Resume PDF file not found at: {pdf_path}")

    # Step 1: Agent 1 - Resume Parser
    with console.status("[bold blue]📋 [Agent 1] Parsing Candidate Resume PDF...", spinner="dots"):
        claims = parse_resume(pdf_path)

    # Resolve GitHub username (either passed via flag or discovered in PDF)
    resolved_github = github_username or claims.github_username or "octocat"

    # Step 2: Agent 2 - GitHub Code Auditor
    with console.status(f"[bold magenta]🔍 [Agent 2] Auditing GitHub profile @{resolved_github}...", spinner="dots"):
        evidence = audit_github(resolved_github)

    # Step 3: Agent 3 - Cross-Auditor & Evaluator
    with console.status("[bold green]📊 [Agent 3] Evaluating Claims vs Evidence & Generating Scorecard...", spinner="dots"):
        scorecard = evaluate_candidate(claims, evidence)

    # Display Results in Terminal
    _display_scorecard(claims, evidence, scorecard)

    # Save report
    if save_report:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        safe_name = "".join(c for c in claims.name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        report_file = reports_dir / f"{safe_name.lower()}_scorecard.json"
        with open(report_file, "w") as f:
            json.dump(scorecard.model_dump(), f, indent=2)
        console.print(f"[dim]📁 Detailed JSON report saved to: [bold]{report_file}[/bold][/dim]\n")

    return scorecard

def _display_scorecard(claims: CandidateClaims, evidence: GitHubEvidence, scorecard: ScreeningScorecard) -> None:
    # Verdict styling
    verdict_colors = {
        "SHORTLIST": "green",
        "REVIEW": "yellow",
        "REJECT": "red"
    }
    verdict_color = verdict_colors.get(scorecard.recommendation, "white")

    # 1. Summary Header
    header_content = (
        f"[bold]Candidate:[/bold] {claims.name}   |   "
        f"[bold]GitHub:[/bold] @{evidence.username}   |   "
        f"[bold]Exp:[/bold] {claims.years_experience or 'N/A'} yrs\n"
        f"[bold]Recommendation:[/bold] [{verdict_color} bold]{scorecard.recommendation}[/{verdict_color} bold]   |   "
        f"[bold]Overall Score:[/bold] [{verdict_color} bold]{scorecard.overall_score}/100[/{verdict_color} bold]"
    )
    console.print(Panel(header_content, title="Candidate Assessment", border_style=verdict_color))

    # 2. Score Breakdown Table
    score_table = Table(box=box.ROUNDED, expand=True)
    score_table.add_column("Metric", style="bold cyan")
    score_table.add_column("Score", justify="center")
    score_table.add_column("Benchmark / Weight", style="dim")

    score_table.add_row(
        "Technical Skills Match",
        f"[bold]{scorecard.skills_match_score}/100[/bold]",
        "40% weight - Claimed vs verified language evidence"
    )
    score_table.add_row(
        "Code Quality & Practice",
        f"[bold]{scorecard.code_quality_score}/100[/bold]",
        "30% weight - Docs ratio, stars, original repo count"
    )
    score_table.add_row(
        "Claim Consistency",
        f"[bold]{scorecard.consistency_score}/100[/bold]",
        "30% weight - Experience timeline & recent activity"
    )
    score_table.add_row(
        "[bold]TOTAL COMPOSITE SCORE[/bold]",
        f"[{verdict_color} bold]{scorecard.overall_score}/100[/{verdict_color} bold]",
        "Overall candidate viability index"
    )
    console.print(score_table)

    # 3. Evidence & Claims Side-by-Side
    evidence_table = Table(box=box.ROUNDED, expand=True)
    evidence_table.add_column("Resume Claims", style="blue")
    evidence_table.add_column("GitHub Public Evidence", style="magenta")

    claimed_str = "\n".join([
        f"• Languages: {', '.join(claims.claimed_languages[:5])}",
        f"• Frameworks: {', '.join(claims.claimed_frameworks[:5])}",
        f"• Tools: {', '.join(claims.claimed_tools[:4])}"
    ])
    
    top_langs = ", ".join([f"{k} ({v})" for k, v in list(evidence.languages_detected.items())[:4]]) or "None detected"
    evidence_str = "\n".join([
        f"• Public Repos: {evidence.total_public_repos} ({evidence.original_repos_count} original, {evidence.forked_repos_count} forks)",
        f"• Languages Detected: {top_langs}",
        f"• Total Stars: {evidence.total_stars} ⭐",
        f"• Documentation: {int(evidence.documentation_ratio * 100)}% repos documented",
        f"• Active Repos (180d): {evidence.recent_activity_count}"
    ])
    
    evidence_table.add_row(claimed_str, evidence_str)
    console.print(evidence_table)

    # 4. Flags & Executive Summary
    flags_table = Table(box=box.ROUNDED, expand=True)
    flags_table.add_column("🟢 Strengths / Green Flags", style="green")
    flags_table.add_column("🔴 Red Flags & Discrepancies", style="red")

    green_str = "\n".join([f"✓ {f}" for f in scorecard.green_flags]) if scorecard.green_flags else "None noted."
    red_str = "\n".join([f"✗ {f}" for f in scorecard.red_flags]) if scorecard.red_flags else "No major red flags detected."
    flags_table.add_row(green_str, red_str)
    console.print(flags_table)

    console.print(Panel(
        f"[italic]{scorecard.executive_summary}[/italic]",
        title="Executive Hiring Summary",
        border_style="dim"
    ))

def main():
    parser = argparse.ArgumentParser(description="AI Resume & GitHub Evidence Screener")
    parser.add_argument("--resume", "-r", type=str, default="sample_resume.pdf", help="Path to resume PDF file")
    parser.add_argument("--github", "-g", type=str, default=None, help="GitHub username override (optional)")
    parser.add_argument("--generate-sample", action="store_true", help="Generate a sample resume PDF first")
    
    args = parser.parse_args()

    # Generate sample if requested or missing default
    if args.generate_sample or (args.resume == "sample_resume.pdf" and not os.path.exists("sample_resume.pdf")):
        from create_sample_resume import generate_sample_resume
        generate_sample_resume("sample_resume.pdf")

    if not os.path.exists(args.resume):
        console.print(f"[bold red]Error:[/bold red] Resume file not found: {args.resume}")
        sys.exit(1)

    run_screening_pipeline(pdf_path=args.resume, github_username=args.github)

if __name__ == "__main__":
    main()
