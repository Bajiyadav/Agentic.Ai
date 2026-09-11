import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List
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
    required_skills: Optional[List[str]] = None,
    target_role: Optional[str] = None,
    min_experience: Optional[float] = None,
    save_report: bool = True
) -> ScreeningScorecard:
    console.print()
    subtitle = (
        f"[dim]Auditing against role: [bold]{target_role}[/bold][/dim]\n"
        f"[dim]Required Skills: {', '.join(required_skills)}[/dim]"
        if required_skills
        else "[dim]Auditing Candidate Claims vs Actual Public GitHub Evidence[/dim]"
    )
    console.print(Panel.fit(
        f"[bold cyan]🔍 AI RESUME & CODE EVIDENCE SCREENER[/bold cyan]\n{subtitle}",
        border_style="cyan"
    ))
    console.print()

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Resume PDF file not found at: {pdf_path}")

    # Delegate to Unified Single Screening Pipeline (Single Source of Truth)
    from src.services.screening_service import execute_screening_pipeline_core
    with console.status("[bold blue]📋 Screening candidate using unified pipeline...", spinner="dots"):
        res = execute_screening_pipeline_core(
            file_path=pdf_path,
            github_user_override=github_username,
            required_skills=required_skills,
            target_role=target_role,
            min_experience=min_experience
        )

    claims = res["claims_obj"]
    evidence = res["evidence_obj"]
    scorecard = res["scorecard_obj"]

    # 🚨 UPFRONT VALIDATION GATE: Early termination for invalid files
    if not res["is_valid_resume"]:
        console.print()
        console.print(Panel.fit(
            f"[bold red]❌ INVALID DOCUMENT DETECTED[/bold red]\n\n"
            f"[bold]Detected Type:[/bold] {res['document_type']}\n"
            f"[bold]Verdict:[/bold] [red bold]REJECT (Score: 0/100)[/red bold]\n\n"
            f"[dim]The uploaded file does not appear to be a professional resume/CV.\n"
            f"Pipeline halted early: skipped GitHub code audit, skipped LLM evaluations.\n"
            f"Please upload the candidate's actual resume PDF.[/dim]",
            title="[red bold]AuditAgent Validation Halt[/red bold]",
            border_style="red"
        ))
        console.print()
        if save_report:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            safe_name = "".join(c for c in claims.name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
            report_file = reports_dir / f"{safe_name.lower()}_scorecard.json"
            with open(report_file, "w") as f:
                json.dump(scorecard.model_dump(), f, indent=2)
            console.print(f"[dim]📁 Detailed JSON report saved to: [bold]{report_file}[/bold][/dim]\n")
        return scorecard

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
    role_info = f"   |   [bold]Role:[/bold] {scorecard.target_role}" if scorecard.target_role else ""
    header_content = (
        f"[bold]Candidate:[/bold] {claims.name}   |   "
        f"[bold]GitHub:[/bold] @{evidence.username}   |   "
        f"[bold]Exp:[/bold] {claims.years_experience or 'N/A'} yrs{role_info}\n"
        f"[bold]Recommendation:[/bold] [{verdict_color} bold]{scorecard.recommendation}[/{verdict_color} bold]   |   "
        f"[bold]Overall Score:[/bold] [{verdict_color} bold]{scorecard.overall_score}/100[/{verdict_color} bold]"
    )
    title = f"Candidate Assessment ({scorecard.target_role})" if scorecard.target_role else "Candidate Assessment"
    console.print(Panel(header_content, title=title, border_style=verdict_color))

    # 2. Score Breakdown Table
    score_table = Table(box=box.ROUNDED, expand=True)
    score_table.add_column("Metric", style="bold cyan")
    score_table.add_column("Score", justify="center")
    score_table.add_column("Benchmark / Weight", style="dim")

    if scorecard.company_skills_match_score is not None:
        score_table.add_row(
            "Company Required Skills Match",
            f"[bold]{scorecard.company_skills_match_score}/100[/bold]",
            "40% weight - Code-verified & claimed match against company requirements"
        )
        score_table.add_row(
            "Technical Skills Match",
            f"[bold]{scorecard.skills_match_score}/100[/bold]",
            "15% weight - Resume claimed vs code detected languages"
        )
        score_table.add_row(
            "Code Quality & Practice",
            f"[bold]{scorecard.code_quality_score}/100[/bold]",
            "25% weight - Docs ratio, stars, original repo count"
        )
        score_table.add_row(
            "Claim Consistency",
            f"[bold]{scorecard.consistency_score}/100[/bold]",
            "20% weight - Experience timeline & recent activity"
        )
        score_table.add_row(
            "[bold]TOTAL COMPOSITE SCORE[/bold]",
            f"[{verdict_color} bold]{scorecard.overall_score}/100[/{verdict_color} bold]",
            "Overall role hiring index"
        )
    else:
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

    # 3. Company Required Skills Breakdown Table (if provided)
    if scorecard.company_required_skills:
        req_table = Table(box=box.ROUNDED, expand=True)
        req_table.add_column("Company Required Skill", style="bold cyan")
        req_table.add_column("Audit Status", justify="center")
        req_table.add_column("Evidence Source & Finding", style="dim")

        for skill in scorecard.company_required_skills:
            if skill in scorecard.verified_company_skills:
                req_table.add_row(
                    skill,
                    "[bold green]✓ VERIFIED IN CODE[/bold green]",
                    "Demonstrated in public GitHub repositories"
                )
            elif skill in scorecard.matched_company_skills:
                req_table.add_row(
                    skill,
                    "[bold yellow]⚠ CLAIMED ONLY[/bold yellow]",
                    "Claimed on resume, but no public GitHub code found"
                )
            else:
                req_table.add_row(
                    skill,
                    "[bold red]✗ MISSING[/bold red]",
                    "Absent from both resume claims and GitHub code"
                )
        console.print(req_table)

    # 4. Evidence & Claims Side-by-Side
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

    # 5. Flags & Executive Summary
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

    # 6. Topic-Focused Interview Questions Targeting Gaps / Discrepancies
    if scorecard.topic_interview_questions:
        q_table = Table(title="🎙️ Topic-Focused Technical Interview Questions (Targeting Discrepancies & Gaps)", box=box.ROUNDED, expand=True)
        q_table.add_column("Topic / Focus Area", style="cyan", width=24)
        q_table.add_column("Recommended Question & Evaluation Guide", style="white")

        for q in scorecard.topic_interview_questions:
            badge = "[yellow]Claimed Without Code[/yellow]" if q.status == "CLAIMED_WITHOUT_CODE" else (
                "[red]Missing Mandatory[/red]" if q.status == "MISSING_MANDATORY" else (
                    "[orange3]Experience Gap[/orange3]" if q.status == "EXPERIENCE_GAP" else "[magenta]Code Health[/magenta]"
                )
            )
            content = (
                f"[bold]{q.question}[/bold]\n"
                f"[dim]• Why Ask: {q.rationale}[/dim]\n"
                f"[dim green]• Listen For: {q.ideal_response_guide}[/dim green]"
            )
            q_table.add_row(f"[bold]{q.topic}[/bold]\n{badge}\n[dim]Difficulty: {q.difficulty}[/dim]", content)

        console.print(q_table)

def main():
    parser = argparse.ArgumentParser(description="AI Resume & GitHub Evidence Screener with Company Requirements")
    parser.add_argument("--resume", "--pdf", "-r", type=str, default="sample_resume.pdf", help="Path to resume PDF file")
    parser.add_argument("--github", "-g", type=str, default=None, help="GitHub username override (optional)")
    parser.add_argument(
        "--skills", "-s",
        type=str,
        default=None,
        help="Company required skills, comma-separated (e.g. --skills 'Python, FastAPI, Docker, PostgreSQL')"
    )
    parser.add_argument(
        "--role",
        type=str,
        default=None,
        help="Company target job role / title (e.g. --role 'Senior Backend Engineer')"
    )
    parser.add_argument(
        "--min-exp",
        type=float,
        default=None,
        help="Company minimum years of experience required (e.g. --min-exp 3.0)"
    )
    parser.add_argument(
        "--description", "-d",
        type=str,
        default=None,
        help="Job description paragraph from which to extract requirements and audit candidate."
    )
    parser.add_argument(
        "--jd",
        type=str,
        default=None,
        help="Path to Job Description file (.txt, .md) to auto-extract company skills"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Prompt interactively for company requirements"
    )
    parser.add_argument("--generate-sample", action="store_true", help="Generate a sample resume PDF first")
    
    args = parser.parse_args()

    # Generate sample if requested or missing default
    if args.generate_sample or (args.resume == "sample_resume.pdf" and not os.path.exists("sample_resume.pdf")):
        from create_sample_resume import generate_sample_resume
        generate_sample_resume("sample_resume.pdf")

    if not os.path.exists(args.resume):
        console.print(f"[bold red]Error:[/bold red] Resume file not found: {args.resume}")
        sys.exit(1)

    required_skills = None
    target_role = args.role
    min_exp = args.min_exp

    if args.skills:
        required_skills = [s.strip() for s in args.skills.split(",") if s.strip()]
    elif args.description:
        from src.services.jd_service import parse_job_description
        parsed_jd = parse_job_description(args.description)
        required_skills = parsed_jd.required_skills
        if not target_role:
            target_role = parsed_jd.title
        if min_exp is None:
            min_exp = parsed_jd.experience_min_years
        console.print(f"[bold green]✓ Extracted from Job Description Paragraph:[/bold green] Role: [cyan]{target_role}[/cyan] | Exp: [cyan]{min_exp}+ yrs[/cyan] | Skills: [cyan]{', '.join(required_skills)}[/cyan]")
    elif args.jd:
        if not os.path.exists(args.jd):
            console.print(f"[bold red]Error:[/bold red] Job description file not found: {args.jd}")
            sys.exit(1)
        from src.services.jd_service import parse_job_description
        with open(args.jd, "r") as f:
            parsed_jd = parse_job_description(f.read())
            required_skills = parsed_jd.required_skills
            if not target_role:
                target_role = parsed_jd.title
            if min_exp is None:
                min_exp = parsed_jd.experience_min_years
            console.print(f"[bold green]✓ Loaded Job Description:[/bold green] {target_role} ({', '.join(required_skills)})")
    elif args.interactive or (sys.stdin.isatty() and len(sys.argv) == 1):
        console.print(Panel.fit(
            "[bold cyan]Company Requirements (Optional)[/bold cyan]\n"
            "[dim]Specify company skills to audit against, or press Enter to skip.[/dim]",
            border_style="cyan"
        ))
        try:
            in_role = console.input("[bold cyan]• Target Job Role (or press Enter to skip): [/bold cyan]").strip()
            if in_role:
                target_role = in_role
            in_skills = console.input("[bold cyan]• Required Skills [comma-separated, e.g. Python, FastAPI, Docker] (or press Enter to skip): [/bold cyan]").strip()
            if in_skills:
                required_skills = [s.strip() for s in in_skills.split(",") if s.strip()]
            in_exp = console.input("[bold cyan]• Minimum Experience in Years (or press Enter to skip): [/bold cyan]").strip()
            if in_exp:
                try:
                    min_exp = float(in_exp)
                except ValueError:
                    pass
            console.print()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Skipping interactive input...[/yellow]\n")

    run_screening_pipeline(
        pdf_path=args.resume,
        github_username=args.github,
        required_skills=required_skills,
        target_role=target_role,
        min_experience=min_exp
    )

if __name__ == "__main__":
    main()

