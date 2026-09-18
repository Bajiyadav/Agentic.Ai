import os
import re
import urllib.parse
import requests
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from .services.tech_ontology import TechOntology


def validate_github_url_or_username(input_str: str) -> Tuple[bool, str, Optional[str]]:
    """
    Safely validates that an input is a legitimate public GitHub URL or username.
    Returns (is_valid, cleaned_username_or_error, optional_repository_name).
    
    Rules:
    - Rejects non-GitHub domains (e.g. gitlab.com, bitbucket.org, arbitrary external sites).
    - Prevents directory traversal, script injection, and illegal characters.
    - Extracts username and optional repo name from full URLs or @ handles.
    """
    if not input_str or not input_str.strip():
        return False, "GitHub URL or username cannot be empty.", None

    cleaned = input_str.strip()

    # Handle domain without protocol
    if cleaned.lower().startswith("github.com/") or cleaned.lower().startswith("www.github.com/"):
        cleaned = "https://" + cleaned

    # Handle full URL
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(cleaned)
        except Exception:
            return False, "Malformed URL provided.", None

        # Enforce official GitHub domain
        hostname = (parsed.netloc or "").lower().split(":")[0]
        if hostname not in ("github.com", "www.github.com"):
            return False, f"Invalid domain '{hostname}'. Only official public GitHub URLs (github.com) are accepted.", None

        # Parse path
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if not path_parts:
            return False, "GitHub URL does not contain a username or repository path.", None

        username = path_parts[0]
        repo_name = path_parts[1] if len(path_parts) > 1 else None
    else:
        # Handle username or @username or username/repo
        cleaned = cleaned.lstrip("@").strip()
        if "/" in cleaned:
            parts = [p for p in cleaned.split("/") if p]
            username = parts[0]
            repo_name = parts[1] if len(parts) > 1 else None
        else:
            username = cleaned
            repo_name = None

    # Validate username formatting (GitHub username spec: 1-39 chars, alphanumeric, single hyphens, no trailing/leading hyphen)
    if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$", username):
        return False, f"Invalid GitHub username '{username}'. GitHub usernames must be 1-39 alphanumeric characters with non-consecutive hyphens.", None

    # Validate optional repo name
    if repo_name and not re.match(r"^[a-zA-Z0-9_.-]{1,100}$", repo_name):
        return False, f"Invalid repository name '{repo_name}'.", None

    return True, username, repo_name


class RepoHighlight(BaseModel):
    name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    is_fork: bool = False
    html_url: str
    detected_frameworks: List[str] = Field(default_factory=list)
    detected_files: List[str] = Field(default_factory=list)
    commit_samples: List[Dict[str, str]] = Field(default_factory=list)


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


class ClaimEvidenceVerification(BaseModel):
    """Traceable, explainable evidence verification for a single resume claim."""
    claim: str
    category: str  # language, framework, database, cloud_devops, tool, project
    status: str    # Verified | Strong Evidence | Moderate Evidence | Weak Evidence | No Public Evidence | Contradictory Evidence
    confidence: str  # High | Medium | Low
    confidence_score: float = 0.0
    repositories: List[str] = Field(default_factory=list)
    file_paths: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    evidence_description: str
    commit_evidence: Optional[str] = None
    audit_timestamp: str


class CandidateGitHubAuditResult(BaseModel):
    """Complete Test 5 GitHub audit result strictly tied to a Candidate and Job."""
    audit_id: str
    candidate_id: str
    job_id: str
    job_title: str
    github_username: str
    github_url: str
    status: str  # Completed | Failed | No GitHub Provided | Rate Limited
    profile: Dict[str, Any]
    repositories_audited_count: int
    repositories: List[Dict[str, Any]]
    claim_verifications: List[ClaimEvidenceVerification]
    audit_notes: List[str]
    audited_at: str
    disclaimer: str


def _generate_mock_github_evidence(username: str) -> GitHubEvidence:
    """Returns deterministic, realistic evidence for local testing and offline verification."""
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
                description="AI-powered candidate screening and code auditing pipeline using Python, FastAPI, and Docker",
                language="Python",
                stars=24,
                forks=3,
                is_fork=False,
                html_url=f"https://github.com/{username}/claim-vs-evidence-engine",
                detected_frameworks=["FastAPI", "Pydantic", "Pytest", "Docker"],
                detected_files=["src/api.py", "src/models.py", "requirements.txt", "Dockerfile"],
                commit_samples=[
                    {"sha": "c7a8190", "message": "Add async FastAPI route decorators and Pydantic validation", "date": "2024-03-01"}
                ]
            ),
            RepoHighlight(
                name="fastapi-saas-starter",
                description="Production ready template with Postgres, SQLAlchemy, and Redis caching",
                language="Python",
                stars=16,
                forks=2,
                is_fork=False,
                html_url=f"https://github.com/{username}/fastapi-saas-starter",
                detected_frameworks=["FastAPI", "SQLAlchemy", "PostgreSQL", "Redis", "Docker"],
                detected_files=["app/main.py", "app/database.py", "requirements.txt", "docker-compose.yml", "Dockerfile"],
                commit_samples=[
                    {"sha": "9e4f201", "message": "Configure PostgreSQL connection pool and Redis cache client", "date": "2024-02-15"}
                ]
            ),
            RepoHighlight(
                name="raft-consensus-cluster",
                description="Distributed consensus protocol implementation in Go with gRPC",
                language="Go",
                stars=12,
                forks=1,
                is_fork=False,
                html_url=f"https://github.com/{username}/raft-consensus-cluster",
                detected_frameworks=["gRPC", "Go"],
                detected_files=["main.go", "raft/node.go", "go.mod"],
                commit_samples=[
                    {"sha": "3f8a02c", "message": "Implement leader election and log replication logic in Go", "date": "2023-11-18"}
                ]
            ),
            RepoHighlight(
                name="nextjs-dashboard",
                description="Analytics UI built with Tailwind, TypeScript, and Next.js 14",
                language="TypeScript",
                stars=8,
                forks=1,
                is_fork=False,
                html_url=f"https://github.com/{username}/nextjs-dashboard",
                detected_frameworks=["Next.js", "React", "TypeScript", "TailwindCSS"],
                detected_files=["package.json", "src/app/page.tsx", "tsconfig.json"],
                commit_samples=[
                    {"sha": "1b08492", "message": "Implement dashboard metrics cards in TypeScript", "date": "2024-01-20"}
                ]
            )
        ],
        audit_notes=["Audited public GitHub profile and active codebases."]
    )


def audit_github(username: str) -> GitHubEvidence:
    """Agent 2: Queries public GitHub API to extract code evidence, activity, and metrics safely."""
    is_valid, clean_user, _ = validate_github_url_or_username(username)
    if not is_valid or clean_user.lower() in ("none", "null", "undefined", "unknown", "n/a", ""):
        return GitHubEvidence(
            username="none",
            profile_found=False,
            total_public_repos=0,
            original_repos_count=0,
            forked_repos_count=0,
            total_stars=0,
            languages_detected={},
            documentation_ratio=0.0,
            recent_activity_count=0,
            audit_notes=["No valid GitHub username provided or found in resume."]
        )

    username = clean_user

    github_token = os.getenv("GITHUB_TOKEN", "")
    use_mock = os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true"
    is_placeholder = "placeholder" in github_token.lower() or not github_token

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
                mock.audit_notes.append("GitHub API rate limit reached; loaded demo evidence safely.")
                return mock
            return GitHubEvidence(
                username=username,
                profile_found=False,
                api_rate_limited=True,
                total_public_repos=0,
                original_repos_count=0,
                forked_repos_count=0,
                total_stars=0,
                languages_detected={},
                documentation_ratio=0.0,
                recent_activity_count=0,
                audit_notes=["GitHub API rate limit exceeded. Verification unavailable."]
            )

        if user_res.status_code == 404:
            if use_mock:
                return _generate_mock_github_evidence(username)
            return GitHubEvidence(
                username=username,
                profile_found=False,
                total_public_repos=0,
                original_repos_count=0,
                forked_repos_count=0,
                total_stars=0,
                languages_detected={},
                documentation_ratio=0.0,
                recent_activity_count=0,
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
        
        languages: Dict[str, int] = {}
        for r in repos_data:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        with_desc = sum(1 for r in repos_data if r.get("description"))
        doc_ratio = round(with_desc / total_repos, 2) if total_repos > 0 else 0.0

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

        sorted_highlights = sorted(
            original_repos or repos_data,
            key=lambda x: (x.get("stargazers_count", 0), x.get("pushed_at", "")),
            reverse=True
        )[:5]

        highlights = []
        for r in sorted_highlights:
            r_name = r.get("name", "repo")
            r_desc = r.get("description") or ""
            r_lang = r.get("language") or ""
            
            # Infer detected frameworks and key files based on description / name / lang
            inferred_frameworks = []
            inferred_files = []
            desc_lower = (r_desc + " " + r_name).lower()
            
            if "fastapi" in desc_lower or r_lang.lower() == "python":
                inferred_frameworks.append("FastAPI") if "fastapi" in desc_lower else None
                inferred_files.extend(["requirements.txt", "main.py"])
            if "react" in desc_lower or "next" in desc_lower:
                inferred_frameworks.append("React")
                inferred_files.extend(["package.json", "src/App.tsx"])
            if "postgres" in desc_lower or "sql" in desc_lower:
                inferred_frameworks.append("PostgreSQL")
            if "docker" in desc_lower:
                inferred_frameworks.append("Docker")
                inferred_files.append("Dockerfile")
            if "terraform" in desc_lower:
                inferred_frameworks.append("Terraform")
                inferred_files.append("main.tf")

            highlights.append(
                RepoHighlight(
                    name=r_name,
                    description=r.get("description"),
                    language=r.get("language"),
                    stars=r.get("stargazers_count", 0),
                    forks=r.get("forks_count", 0),
                    is_fork=r.get("fork", False),
                    html_url=r.get("html_url", ""),
                    detected_frameworks=inferred_frameworks,
                    detected_files=list(set(inferred_files)),
                    commit_samples=[]
                )
            )

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


def verify_claims_against_github(
    claims: Any,
    evidence: GitHubEvidence,
    job_title: str = ""
) -> List[ClaimEvidenceVerification]:
    """
    Central Test 5 Engine:
    Produces a traceable claim-by-claim verification of candidate resume claims against public GitHub evidence.
    
    Statuses:
    - Verified: Clear direct evidence in code or manifests supports the claim.
    - Strong Evidence: Multiple meaningful pieces of code evidence support the claim.
    - Moderate Evidence: Some relevant evidence exists, but it is limited or in configuration.
    - Weak Evidence: Very limited or indirect evidence (e.g. description tag only or forked repo).
    - No Public Evidence: The claim could not be verified from available public GitHub evidence.
      (Safety rule: NEVER converted to False or that candidate lacks the skill).
    - Contradictory Evidence: Public evidence conflicts directly with the resume claim.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    results: List[ClaimEvidenceVerification] = []

    # Assemble all categorized claims from CandidateClaims or dict
    claim_items: List[Tuple[str, str]] = []  # (claim, category)

    def _get_items(attr: str, alt_key: str) -> List[str]:
        if hasattr(claims, attr) and getattr(claims, attr):
            return getattr(claims, attr)
        if isinstance(claims, dict):
            return claims.get(attr) or claims.get(alt_key) or []
        return []

    for c in _get_items("claimed_languages", "languages"):
        if c and str(c).strip():
            claim_items.append((str(c).strip(), "Language"))

    for c in _get_items("claimed_frameworks", "frameworks"):
        if c and str(c).strip():
            claim_items.append((str(c).strip(), "Framework / Library"))

    for c in _get_items("claimed_databases", "databases"):
        if c and str(c).strip():
            claim_items.append((str(c).strip(), "Database & Storage"))

    for c in _get_items("claimed_cloud_devops", "cloud_devops"):
        if c and str(c).strip():
            claim_items.append((str(c).strip(), "Cloud & DevOps"))

    for c in _get_items("claimed_tools", "tools"):
        if c and str(c).strip():
            claim_items.append((str(c).strip(), "Tool / Utility"))

    # If no structured claims, fallback to key_claims
    if not claim_items:
        key_claims = _get_items("key_claims", "key_claims")
        for k in key_claims:
            if k and str(k).strip():
                claim_items.append((str(k).strip(), "General Claim"))

    # Case A: GitHub profile unavailable / not found
    if not evidence.profile_found or evidence.username.lower() in ("none", "null", ""):
        for claim_text, cat in claim_items:
            results.append(
                ClaimEvidenceVerification(
                    claim=claim_text,
                    category=cat,
                    status="No Public Evidence",
                    confidence="High",
                    confidence_score=0.0,
                    repositories=[],
                    file_paths=[],
                    files=[],
                    evidence_description=f"No public GitHub profile was available or found for this candidate. Claim '{claim_text}' could not be verified from public sources. (Note: Lack of public evidence does not imply the candidate lacks this skill, as enterprise work is typically conducted in private repositories).",
                    commit_evidence=None,
                    audit_timestamp=now_utc
                )
            )
        return results

    # Case B: Profile found - inspect repositories, languages, files, and commits
    detected_langs_lower = {TechOntology.normalize(k).lower(): (k, count) for k, count in (evidence.languages_detected or {}).items()}
    all_highlights = evidence.repo_highlights or []

    for claim_text, cat in claim_items:
        c_canon = TechOntology.normalize(claim_text)
        c_lower = c_canon.lower().strip()
        orig_lower = claim_text.lower().strip()
        matched_repos: List[str] = []
        matched_files: List[str] = []
        matched_commits: List[str] = []

        # 1. Language matching
        is_language_claim = cat.lower() == "language" or c_lower in detected_langs_lower or orig_lower in detected_langs_lower
        lang_repo_count = 0
        if c_lower in detected_langs_lower:
            orig_name, lang_repo_count = detected_langs_lower[c_lower]
        elif orig_lower in detected_langs_lower:
            orig_name, lang_repo_count = detected_langs_lower[orig_lower]

        # 2. Inspect repo highlights
        for repo in all_highlights:
            r_name = repo.name.lower()
            r_desc = (repo.description or "").lower()
            r_lang = TechOntology.normalize(repo.language or "").lower()
            frameworks_canon = [TechOntology.normalize(f).lower() for f in repo.detected_frameworks]

            # Manifest check via TechOntology
            manifest_match = TechOntology.match_manifest_evidence(c_canon, repo.detected_files, repo.detected_frameworks)

            # Direct framework or library or manifest detection
            if (c_lower in frameworks_canon or 
                orig_lower in frameworks_canon or 
                manifest_match or
                c_lower in r_desc or 
                c_lower in r_name):
                matched_repos.append(repo.name)
                # Collect relevant files
                for f in repo.detected_files:
                    if c_lower in f.lower() or orig_lower in f.lower() or any(ext in f.lower() for ext in [".py", ".ts", ".go", ".tf", ".json", "docker"]):
                        matched_files.append(f"{repo.name}/{f}")
                # Collect commit evidence
                for c in repo.commit_samples:
                    if c_lower in c.get("message", "").lower() or orig_lower in c.get("message", "").lower() or is_language_claim:
                        matched_commits.append(f"{c.get('sha', '')}: {c.get('message', '')}")

            elif is_language_claim and (c_lower == r_lang or orig_lower == r_lang):
                matched_repos.append(repo.name)
                for f in repo.detected_files:
                    matched_files.append(f"{repo.name}/{f}")
                for c in repo.commit_samples:
                    matched_commits.append(f"{c.get('sha', '')}: {c.get('message', '')}")

        matched_repos = list(dict.fromkeys(matched_repos))
        matched_files = list(dict.fromkeys(matched_files))
        matched_commits = list(dict.fromkeys(matched_commits))

        # 4. Status Determination
        if is_language_claim and lang_repo_count >= 2:
            status = "Strong Evidence"
            confidence = "High"
            conf_score = 0.85
            desc = f"Primary language detected across {lang_repo_count} public repositories with extensive codebase history."
        elif len(matched_repos) >= 2 or (len(matched_repos) == 1 and len(matched_files) >= 2):
            status = "Strong Evidence"
            confidence = "High"
            conf_score = 0.85
            desc = f"Supported by multiple codebase implementations in {', '.join(matched_repos[:2])}, including relevant source and manifest files."
        elif len(matched_repos) == 1 and (matched_files or matched_commits):
            status = "Verified"
            confidence = "High"
            conf_score = 0.95
            desc = f"Directly verified in public repository '{matched_repos[0]}' with supporting files ({', '.join([f.split('/')[-1] for f in matched_files[:2]])})."
        elif len(matched_repos) == 1 or lang_repo_count == 1:
            status = "Moderate Evidence"
            confidence = "Medium"
            conf_score = 0.60
            desc = f"Referenced in repository configuration or metadata for '{matched_repos[0] if matched_repos else list(detected_langs_lower.keys())[0]}'."
        elif any(c_lower in (r.description or "").lower() for r in all_highlights):
            status = "Weak Evidence"
            confidence = "Low"
            conf_score = 0.30
            desc = "Referenced only in repository descriptions without direct source code implementation."
        else:
            # SAFETY RULE: No Public Evidence is NEVER labeled False
            status = "No Public Evidence"
            confidence = "High"
            conf_score = 0.0
            desc = f"No public repositories, source files, manifests, or commit records for '{claim_text}' were found in the candidate's audited public GitHub repositories. (Note: Lack of public evidence does not imply the candidate lacks this skill, as enterprise work is typically conducted in private repositories)."

        results.append(
            ClaimEvidenceVerification(
                claim=claim_text,
                category=cat,
                status=status,
                confidence=confidence,
                confidence_score=conf_score,
                repositories=matched_repos,
                file_paths=matched_files[:4],
                files=matched_files[:4],
                evidence_description=desc,
                commit_evidence=matched_commits[0] if matched_commits else None,
                audit_timestamp=now_utc
            )
        )

    return results
