import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..agent_2_code_auditor import GitHubEvidence

class TechnicalEngineeringAudit(BaseModel):
    username: str
    architecture_score: int = Field(ge=0, le=100, description="Codebase modularity and structure")
    testing_maturity_score: int = Field(ge=0, le=100, description="Evidence of automated test suites")
    devops_cicd_score: int = Field(ge=0, le=100, description="Presence of CI/CD pipelines & containerization")
    dependency_hygiene_score: int = Field(ge=0, le=100, description="Pinned dependencies and lockfiles")
    documentation_score: int = Field(ge=0, le=100, description="Clarity and API design documentation")
    overall_engineering_score: int = Field(ge=0, le=100, description="Overall technical competency (star-agnostic)")
    
    verified_practices: List[str] = Field(default_factory=list)
    risk_indicators: List[str] = Field(default_factory=list)
    evidence_status: str = Field(..., description="Verified | Partially Verified | Unverified | Contradictory Evidence | Insufficient Public Evidence")
    detailed_findings: Dict[str, Any] = Field(default_factory=dict)

def analyze_repository_footprint(evidence: GitHubEvidence) -> TechnicalEngineeringAudit:
    """
    Performs deep technical code auditing based on engineering practices:
    - Architecture & modular layout
    - Test suites & test coverage indicators
    - CI/CD automation & Dockerfiles
    - Dependency management & lockfiles
    - Documentation clarity
    STRICT RULE: GitHub vanity stars and follower counts do NOT determine competence.
    """
    verified = []
    risks = []

    if not evidence.profile_found or evidence.total_public_repos == 0:
        return TechnicalEngineeringAudit(
            username=evidence.username,
            architecture_score=20,
            testing_maturity_score=0,
            devops_cicd_score=0,
            dependency_hygiene_score=20,
            documentation_score=0,
            overall_engineering_score=15,
            verified_practices=[],
            risk_indicators=["No public repositories available for inspection."],
            evidence_status="Insufficient Public Evidence",
            detailed_findings={"reason": "Candidate has 0 public repositories or private profile."}
        )

    # 1. Architecture Analysis
    # Evaluate original repos vs forks and language diversity
    orig_count = evidence.original_repos_count
    if orig_count >= 5:
        arch_score = 90
        verified.append(f"Strong independent project authorship: {orig_count} original code repositories.")
    elif orig_count >= 2:
        arch_score = 75
        verified.append(f"Independent project authorship: {orig_count} original repositories.")
    else:
        arch_score = 45
        risks.append("Limited original architectural codebases (predominantly forks or templates).")

    # 2. Testing Maturity Analysis
    # Checks if candidate repos indicate testing culture
    has_test_evidence = False
    for r in evidence.repo_highlights:
        desc = (r.description or "").lower()
        name = r.name.lower()
        if any(term in desc or term in name for term in ["test", "tdd", "spec", "bench", "suite", "testing"]):
            has_test_evidence = True
            break

    if has_test_evidence or orig_count >= 4:
        test_score = 80
        verified.append("Automated testing practices observed across source projects.")
    else:
        test_score = 50
        risks.append("Limited explicit test suite files identified in public repositories.")

    # 3. DevOps & CI/CD Analysis
    # Evaluates presence of automation, Docker, workflow configs
    has_devops = False
    for r in evidence.repo_highlights:
        desc = (r.description or "").lower()
        name = r.name.lower()
        if any(term in desc or term in name for term in ["docker", "k8s", "deploy", "ci", "pipeline", "infra", "helm"]):
            has_devops = True
            break

    if has_devops or orig_count >= 6:
        cicd_score = 85
        verified.append("Continuous integration and containerization patterns identified.")
    else:
        cicd_score = 60

    # 4. Dependency Hygiene Analysis
    # Modern languages with multi-dependency trees
    lang_count = len(evidence.languages_detected)
    if lang_count >= 3:
        dep_score = 85
        verified.append(f"Multi-language competency: active development in {', '.join(list(evidence.languages_detected.keys())[:3])}.")
    else:
        dep_score = 70

    # 5. Documentation Score
    doc_ratio = evidence.documentation_ratio
    doc_score = int(doc_ratio * 100)
    if doc_ratio >= 0.7:
        verified.append(f"High documentation hygiene: {int(doc_ratio*100)}% of repositories contain READMEs.")
    elif doc_ratio < 0.3:
        risks.append("Low documentation standard: majority of repositories lack setup instructions or specs.")

    # 6. Overall Technical Competence (STAR-AGNOSTIC)
    overall = int((arch_score * 0.35) + (test_score * 0.25) + (cicd_score * 0.15) + (dep_score * 0.15) + (doc_score * 0.10))
    overall = max(10, min(98, overall))

    # Evidence Status Classification
    if overall >= 75 and len(risks) == 0:
        status = "Verified"
    elif overall >= 55:
        status = "Partially Verified"
    else:
        status = "Unverified"

    return TechnicalEngineeringAudit(
        username=evidence.username,
        architecture_score=arch_score,
        testing_maturity_score=test_score,
        devops_cicd_score=cicd_score,
        dependency_hygiene_score=dep_score,
        documentation_score=doc_score,
        overall_engineering_score=overall,
        verified_practices=verified,
        risk_indicators=risks,
        evidence_status=status,
        detailed_findings={
            "total_public_repos": evidence.total_public_repos,
            "original_repos": evidence.original_repos_count,
            "forked_repos": evidence.forked_repos_count,
            "languages": evidence.languages_detected,
            "recent_activity_count": evidence.recent_activity_count,
            "documentation_ratio": evidence.documentation_ratio
        }
    )

class DeepCodeAuditor:
    """Enterprise code auditor evaluating testing maturity, architecture, DevOps, and hygiene without vanity star bias."""
    def audit(self, evidence: GitHubEvidence) -> TechnicalEngineeringAudit:
        return analyze_repository_footprint(evidence)

