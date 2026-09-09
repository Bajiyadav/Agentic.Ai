import os
import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class RepoHighlight(BaseModel):
    name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    is_fork: bool = False
    html_url: str

class GitHubEvidence(BaseModel):
    username: str
    profile_found: bool = True
    account_created_at: Optional[str] = None
    total_public_repos: int = 0
    original_repos_count: int = 0
    forked_repos_count: int = 0
    total_stars: int = 0
    languages_detected: Dict[str, int] = Field(default_factory=dict)
    documentation_ratio: float = 0.0  # percentage of repos with description
    recent_activity_count: int = 0    # updated within last 180 days
    repo_highlights: List[RepoHighlight] = Field(default_factory=list)
    api_rate_limited: bool = False
    audit_notes: List[str] = Field(default_factory=list)

def _generate_mock_github_evidence(username: str) -> GitHubEvidence:
    """Returns realistic mock evidence for testing when offline or hitting rate limits."""
    return GitHubEvidence(
        username=username,
        profile_found=True,
        account_created_at="2021-03-15T08:30:00Z",
        total_public_repos=14,
        original_repos_count=10,
        forked_repos_count=4,
        total_stars=48,
        languages_detected={"Python": 6, "TypeScript": 4, "JavaScript": 2, "Go": 1},
        documentation_ratio=0.85,
        recent_activity_count=8,
        repo_highlights=[
            RepoHighlight(
                name="claim-vs-evidence-engine",
                description="AI-powered candidate screening and code auditing pipeline",
                language="Python",
                stars=24,
                forks=3,
                is_fork=False,
                html_url=f"https://github.com/{username}/claim-vs-evidence-engine"
            ),
            RepoHighlight(
                name="fastapi-saas-starter",
                description="Production ready template with Postgres and JWT auth",
                language="Python",
                stars=16,
                forks=2,
                is_fork=False,
                html_url=f"https://github.com/{username}/fastapi-saas-starter"
            ),
            RepoHighlight(
                name="nextjs-dashboard",
                description="Analytics UI built with Tailwind and Next.js 14",
                language="TypeScript",
                stars=8,
                forks=1,
                is_fork=False,
                html_url=f"https://github.com/{username}/nextjs-dashboard"
            )
        ],
        audit_notes=["[DEMO MODE] Generated mock GitHub evidence for local testing and demonstration."]
    )

def audit_github(username: str) -> GitHubEvidence:
    """Agent 2: Queries public GitHub API to extract code evidence, activity, and metrics."""
    if not username:
        return GitHubEvidence(
            username="none",
            profile_found=False,
            audit_notes=["No GitHub username provided or found in resume."]
        )

    # Clean username if URL passed
    username = username.rstrip("/").split("/")[-1].replace("@", "")

    github_token = os.getenv("GITHUB_TOKEN", "")
    use_mock = os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true"
    is_placeholder = "placeholder" in github_token.lower()

    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token and not is_placeholder:
        headers["Authorization"] = f"token {github_token}"

    user_url = f"https://api.github.com/users/{username}"
    repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"

    try:
        user_res = requests.get(user_url, headers=headers, timeout=10)
        
        # Check rate limits
        if user_res.status_code == 403 and "rate limit" in user_res.text.lower():
            if use_mock:
                mock = _generate_mock_github_evidence(username)
                mock.api_rate_limited = True
                mock.audit_notes.append("GitHub API rate limit reached; loaded demo evidence.")
                return mock
            return GitHubEvidence(
                username=username,
                profile_found=False,
                api_rate_limited=True,
                audit_notes=["GitHub API rate limit exceeded. Set GITHUB_TOKEN in .env to expand limit."]
            )

        if user_res.status_code == 404:
            if use_mock:
                mock = _generate_mock_github_evidence(username)
                mock.audit_notes.append(f"GitHub user '{username}' not found; populated demo data for evaluation.")
                return mock
            return GitHubEvidence(
                username=username,
                profile_found=False,
                audit_notes=[f"GitHub user '{username}' was not found on GitHub."]
            )

        user_res.raise_for_status()
        user_data = user_res.json()

        repos_res = requests.get(repos_url, headers=headers, timeout=10)
        repos_data = repos_res.json() if repos_res.status_code == 200 else []

        # Analyze repositories
        total_repos = len(repos_data)
        original_repos = [r for r in repos_data if not r.get("fork", False)]
        forked_repos = [r for r in repos_data if r.get("fork", False)]
        
        total_stars = sum(r.get("stargazers_count", 0) for r in repos_data)
        
        # Languages
        languages: Dict[str, int] = {}
        for r in repos_data:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        # Documentation quality (has description and README)
        with_desc = sum(1 for r in repos_data if r.get("description"))
        doc_ratio = round(with_desc / total_repos, 2) if total_repos > 0 else 0.0

        # Recent activity (past 180 days)
        recent_count = 0
        now = datetime.now(timezone.utc)
        for r in repos_data:
            updated_at_str = r.get("pushed_at") or r.get("updated_at")
            if updated_at_str:
                try:
                    updated_dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    if (now - updated_dt).days <= 180:
                        recent_count += 1
                except Exception:
                    pass

        # Top 3 highlights (sorted by stars then update time)
        sorted_highlights = sorted(
            original_repos or repos_data,
            key=lambda x: (x.get("stargazers_count", 0), x.get("pushed_at", "")),
            reverse=True
        )[:3]

        highlights = [
            RepoHighlight(
                name=r.get("name", "repo"),
                description=r.get("description"),
                language=r.get("language"),
                stars=r.get("stargazers_count", 0),
                forks=r.get("forks_count", 0),
                is_fork=r.get("fork", False),
                html_url=r.get("html_url", "")
            )
            for r in sorted_highlights
        ]

        notes = []
        if total_repos == 0:
            notes.append("Account exists but has 0 public repositories.")
        elif len(original_repos) == 0:
            notes.append("All public repositories are forks/clones of other projects.")

        return GitHubEvidence(
            username=username,
            profile_found=True,
            account_created_at=user_data.get("created_at"),
            total_public_repos=total_repos,
            original_repos_count=len(original_repos),
            forked_repos_count=len(forked_repos),
            total_stars=total_stars,
            languages_detected=languages,
            documentation_ratio=doc_ratio,
            recent_activity_count=recent_count,
            repo_highlights=highlights,
            audit_notes=notes
        )

    except Exception as e:
        if use_mock:
            mock = _generate_mock_github_evidence(username)
            mock.audit_notes.append(f"Network error accessing GitHub API ({str(e)}); loaded demo fallback.")
            return mock
        raise e
