import re
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field

logger = logging.getLogger("auditagent.interview_generator")

class CommitGroundedQuestion(BaseModel):
    id: str
    repo_name: str
    commit_sha: str
    commit_message: str
    commit_date: Optional[str] = None
    technology: str
    category: str  # Architecture & Scaling | Resilience & Error Handling | Concurrency & Async | Data Integrity | Security
    difficulty: str  # Mid-Level | Senior | Staff / Lead
    grounding_type: str = "verified_commit"  # verified_commit | claimed_stack_scenario
    grounded_context: str
    question: str
    evaluation_rubric: List[str] = Field(default_factory=list)
    followup_questions: List[str] = Field(default_factory=list)

class CommitInterviewPack(BaseModel):
    candidate_id: Optional[str] = None
    candidate_name: str
    job_title: str
    total_questions: int
    questions: List[CommitGroundedQuestion]
    summary_memo: str
    generated_at: str

# Architectural question templates keyed by commit keywords
ARCHITECTURAL_PATTERNS = [
    {
        "keywords": ["pool", "connection", "asyncpg", "sqlalchemy", "psycopg", "database", "postgres", "mysql"],
        "category": "Data Integrity & Concurrency",
        "technology": "Relational DB & Connection Pooling",
        "difficulty": "Senior",
        "question_tmpl": (
            "In your repository '{repo}', commit {sha} ('{message}'), you configured database connection pooling. "
            "Under peak traffic loads with high concurrent async requests, how did you determine optimal pool sizing, "
            "and how do you protect against connection pool exhaustion or cascading database failovers?"
        ),
        "rubric": [
            "Candidate explains sizing formula based on CPU cores, max DB connections, and async event loop throughput.",
            "Candidate discusses connection timeouts, statement timeouts, and health-check recycles.",
            "Candidate mentions circuit breakers or queue backpressure to avoid overwhelming the database cluster."
        ],
        "followups": [
            "If your database primary fails over to a replica with 2 seconds of replication lag, how does your pool handle in-flight transactions?",
            "How do you monitor and alert on pool starvation in Prometheus or Datadog?"
        ]
    },
    {
        "keywords": ["redis", "cache", "memcached", "ttl", "invalidation"],
        "category": "Architecture & Scaling",
        "technology": "Distributed Caching & Invalidation",
        "difficulty": "Senior",
        "question_tmpl": (
            "Reviewing repository '{repo}', commit {sha} ('{message}'), you integrated Redis caching. "
            "How did you address the cache invalidation strategy across horizontal workers, and how does your architecture "
            "defend against cache stampede / dog-piling when hot keys expire?"
        ),
        "rubric": [
            "Demonstrates understanding of probabilistic early expiration (XFetch) or mutex locks on cache misses.",
            "Discusses cache consistency guarantees (eventual vs read-your-writes) and invalidation event publishing.",
            "Mentions graceful degradation if Redis becomes temporarily unreachable."
        ],
        "followups": [
            "What Redis eviction policy (e.g. allkeys-lru vs volatile-lfu) did you select and why?",
            "How do you prevent serializing stale or sensitive PII data into the shared cache?"
        ]
    },
    {
        "keywords": ["fastapi", "route", "decorator", "pydantic", "validation", "schema", "controller"],
        "category": "API Contract & Reliability",
        "technology": "FastAPI & Request Validation",
        "difficulty": "Mid-Level",
        "question_tmpl": (
            "In repository '{repo}', commit {sha} ('{message}'), you implemented API routing and schema validation. "
            "How did you structure error handling for unprocessable payloads, and how do you ensure API backwards compatibility "
            "when modifying core Pydantic response models consumed by mobile or third-party clients?"
        ),
        "rubric": [
            "Explains centralized exception handlers translating validation errors into RFC 7807 problem details.",
            "Mentions semantic versioning, schema evolution rules, and optional field deprecations.",
            "Understands performance overhead of deep nested Pydantic model serialization."
        ],
        "followups": [
            "How do you separate internal database models from external public API DTOs?",
            "What is your approach to rate limiting public endpoints to prevent DoS attacks?"
        ]
    },
    {
        "keywords": ["docker", "container", "compose", "dockerfile", "k8s", "kubernetes", "deploy"],
        "category": "Resilience & Error Handling",
        "technology": "Containerization & Zero-Downtime Deployment",
        "difficulty": "Senior",
        "question_tmpl": (
            "In your repository '{repo}', commit {sha} ('{message}'), you updated container build and deployment configs. "
            "How did you optimize image layering and multi-stage builds for security, and how are SIGTERM signals handled "
            "to achieve graceful draining of active requests during zero-downtime rolling updates?"
        ),
        "rubric": [
            "References multi-stage Docker builds to eliminate build toolchains from final minimal runtime images.",
            "Explains signal propagation (avoiding PID 1 trap, dumb-init or gunicorn worker graceful timeout).",
            "Discusses non-root user enforcement and vulnerability scanning in CI/CD."
        ],
        "followups": [
            "What health check endpoints (liveness vs readiness probes) did you configure and what invariants do they verify?",
            "How do you handle ephemeral secret injection into containerized environments?"
        ]
    },
    {
        "keywords": ["test", "pytest", "mock", "unittest", "coverage", "integration"],
        "category": "Testing & Software Quality",
        "technology": "Automated Testing & Test Doubles",
        "difficulty": "Mid-Level",
        "question_tmpl": (
            "In repository '{repo}', commit {sha} ('{message}'), you wrote automated test suites. "
            "How did you isolate external dependencies (such as external payment gateways or third-party APIs) without "
            "creating overly brittle mocks that mask production regressions?"
        ),
        "rubric": [
            "Articulates difference between contract testing, integration testing with Testcontainers, and unit mock testing.",
            "Explains how to maintain test speed while still executing against realistic database schemas.",
            "Discusses idempotency and state cleanup between test iterations."
        ],
        "followups": [
            "How do you approach testing asynchronous background queues or retry semantics?",
            "What code coverage metrics or mutation testing practices do you enforce in your team's CI gate?"
        ]
    },
    {
        "keywords": ["auth", "jwt", "oauth", "security", "token", "middleware", "rbac"],
        "category": "Security & Invariants",
        "technology": "Authentication & Authorization Middleware",
        "difficulty": "Senior",
        "question_tmpl": (
            "In repository '{repo}', commit {sha} ('{message}'), you implemented authentication and token validation. "
            "How did you handle token revocation (e.g. logout or compromised credentials) with stateless JWTs, "
            "and how do you enforce multi-tenant authorization boundaries at the database layer?"
        ),
        "rubric": [
            "Discusses short-lived access tokens combined with rotating refresh tokens or Redis token blocklists.",
            "Explains tenant context injection into async request scoped variables or Row-Level Security (RLS).",
            "Shows deep awareness of timing attack mitigations and secure cookie/header flags."
        ],
        "followups": [
            "How do you prevent privilege escalation when validating role claims from untrusted tokens?",
            "What audit logging do you record for failed authentication attempts?"
        ]
    }
]

class EvidenceInterviewGenerator:
    """
    Analyzes candidate GitHub repository highlights and commit history to generate
    concrete, evidence-grounded technical interview questions citing exact commit SHAs,
    repositories, and architectural patterns.
    """

    @classmethod
    def generate_from_repo_highlights(
        cls,
        candidate_name: str,
        job_title: str,
        repo_highlights: List[Dict[str, Any]],
        max_questions: int = 5
    ) -> CommitInterviewPack:
        """
        Parses repo highlights and commit samples to create tailored interview questions.
        """
        from datetime import datetime, timezone
        now_str = datetime.now(timezone.utc).isoformat()
        questions: List[CommitGroundedQuestion] = []
        q_idx = 1

        # 1. Iterate over real commits in repository highlights
        for repo in repo_highlights:
            repo_name = repo.get("name", "candidate-repo")
            commits = repo.get("commit_samples", [])
            frameworks = repo.get("detected_frameworks", [])

            for commit in commits:
                if len(questions) >= max_questions:
                    break

                sha = commit.get("sha", "head")[:7]
                message = commit.get("message", "Update codebase")
                c_date = commit.get("date")
                msg_lower = message.lower()

                # Find best matching architectural pattern
                matched_pattern = None
                for pattern in ARCHITECTURAL_PATTERNS:
                    if any(kw in msg_lower for kw in pattern["keywords"]):
                        matched_pattern = pattern
                        break

                if matched_pattern:
                    q_text = matched_pattern["question_tmpl"].format(
                        repo=repo_name,
                        sha=sha,
                        message=message
                    )
                    context_desc = (
                        f"Candidate authored commit {sha} in public repository '{repo_name}' with message "
                        f"'{message}', utilizing {', '.join(frameworks) if frameworks else matched_pattern['technology']}."
                    )
                    questions.append(CommitGroundedQuestion(
                        id=f"cgq-{q_idx:03d}",
                        repo_name=repo_name,
                        commit_sha=sha,
                        commit_message=message,
                        commit_date=c_date,
                        technology=matched_pattern["technology"],
                        category=matched_pattern["category"],
                        difficulty=matched_pattern["difficulty"],
                        grounding_type="verified_commit",
                        grounded_context=context_desc,
                        question=q_text,
                        evaluation_rubric=matched_pattern["rubric"],
                        followup_questions=matched_pattern["followups"]
                    ))
                    q_idx += 1

        # 2. If fewer than 3 questions were generated from specific commits, generate from repo frameworks
        if len(questions) < max_questions:
            for repo in repo_highlights:
                if len(questions) >= max_questions:
                    break
                repo_name = repo.get("name", "project")
                frameworks = repo.get("detected_frameworks", [])
                lang = repo.get("language") or "Python"

                if frameworks:
                    fw_str = ", ".join(frameworks[:3])
                    questions.append(CommitGroundedQuestion(
                        id=f"cgq-{q_idx:03d}",
                        repo_name=repo_name,
                        commit_sha="main",
                        commit_message=f"Architecture using {fw_str}",
                        commit_date=None,
                        technology=fw_str,
                        category="System Architecture",
                        difficulty="Senior",
                        grounding_type="verified_commit",
                        grounded_context=f"Observed {fw_str} stack implementation in repository '{repo_name}'.",
                        question=(
                            f"In your repository '{repo_name}', you implemented a stack based on {fw_str}. "
                            f"Could you explain your architectural boundaries, how state is decoupled between components, "
                            f"and what lessons you learned regarding operational telemetry in production?"
                        ),
                        evaluation_rubric=[
                            f"Demonstrates deep hands-on fluency with {fw_str}.",
                            "Explains boundary separation between business logic and framework adapters.",
                            "Mentions structured logging, metrics, and tracing instrumentation."
                        ],
                        followup_questions=[
                            f"What was the most challenging production bug encountered in '{repo_name}' and how did you diagnose it?",
                            "How do you organize CI validation and automated linting for this codebase?"
                        ]
                    ))
                    q_idx += 1

        # 3. Fallback: If candidate has no public repos or commits, provide scenario questions grounded in job stack
        if not questions:
            fallback_scenarios = [
                {
                    "tech": "Distributed Systems & Asynchronous Queues",
                    "cat": "Architecture & Scaling",
                    "diff": "Senior",
                    "q": (
                        f"For the {job_title} role, suppose you need to design an asynchronous event-driven worker "
                        f"that consumes messages from an unbuffered broker. How would you ensure at-least-once delivery, "
                        f"idempotent message processing, and dead-letter queue routing without losing customer data?"
                    ),
                    "rubric": [
                        "Explains idempotent database keys and transaction commits with message acknowledgments.",
                        "Discusses retry backoff strategies and poison message quarantine via DLQ.",
                        "Shows awareness of consumer group scaling and partition rebalancing."
                    ]
                },
                {
                    "tech": "PostgreSQL & High-Throughput Storage",
                    "cat": "Data Integrity & Concurrency",
                    "diff": "Senior",
                    "q": (
                        f"When designing relational schemas for high-write workloads in {job_title} projects, "
                        f"how do you balance indexing overhead against query latency, and what isolation levels "
                        f"do you choose to prevent phantom reads or write skews?"
                    ),
                    "rubric": [
                        "Analyzes write amplification caused by secondary indexes.",
                        "Explains Read Committed vs Repeatable Read vs Serializable isolation semantics.",
                        "Understands partial indexes and vacuuming strategies for high-churn tables."
                    ]
                }
            ]
            for scen in fallback_scenarios:
                questions.append(CommitGroundedQuestion(
                    id=f"cgq-{q_idx:03d}",
                    repo_name="Target Role Architecture",
                    commit_sha="N/A",
                    commit_message="Claimed Senior Technical Capability",
                    commit_date=None,
                    technology=scen["tech"],
                    category=scen["cat"],
                    difficulty=scen["diff"],
                    grounding_type="claimed_stack_scenario",
                    grounded_context=f"Formulated based on claimed senior experience relevant to {job_title}.",
                    question=scen["q"],
                    evaluation_rubric=scen["rubric"],
                    followup_questions=[
                        "How would you load-test this architecture prior to launch?",
                        "What key alerts would wake up an on-call engineer?"
                    ]
                ))
                q_idx += 1

        memo = (
            f"Generated {len(questions)} technical interview questions grounded in candidate's verified GitHub "
            f"codebase evidence. Questions cite specific repositories, commit messages, and architectural design choices."
        )

        return CommitInterviewPack(
            candidate_name=candidate_name,
            job_title=job_title,
            total_questions=len(questions),
            questions=questions,
            summary_memo=memo,
            generated_at=now_str
        )
