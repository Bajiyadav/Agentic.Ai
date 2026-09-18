# 🤖 AuditAgent.ai — Evidence-Driven Technical Hiring Platform

> ### **AI advises. Evidence explains. Recruiters decide.**

AuditAgent.ai is an evidence-driven technical hiring platform that helps companies evaluate engineering candidates against the actual requirements of a role. It analyzes job descriptions, verifies technical claims against available public code evidence, delivers role-specific technical assessments, and produces explainable candidate recommendations—while keeping the recruiter in control of the final hiring decision.

---

## 📚 Enterprise Documentation & Production Guides

- 🏛️ **[System Architecture Documentation](docs/ARCHITECTURE.md)**: End-to-end technical specification of all 5 pillars, agent workflows, ER diagram, and security isolation.
- 🚀 **[Production Deployment Runbook](docs/PRODUCTION_DEPLOYMENT.md)**: Multi-stage Docker, PostgreSQL 17 + PgBouncer pooling, Redis caching, async workers, Caddy/Nginx TLS, and Prometheus observability.
- ⚖️ **[Legal & Regulatory Compliance Framework](docs/LEGAL_AND_COMPLIANCE.md)**: NYC Local Law 144 (AEDT bias audits, 4/5ths impact ratio), EEOC Title VII / UGESP compliance, and GDPR Article 22 automated decision safeguards.

---

## 🌟 The 5 Core Pillars

1. **01 — Job Intelligence**
   - Understand exactly what the role requires: extracts strict required vs preferred skills, seniority levels, and responsibilities with zero hallucination.

2. **02 — Evidence Audit**
   - Compare candidate claims with available technical evidence: analyzes available public GitHub repositories, repository activity, and code evidence associated with the candidate. Neutral baseline for unlisted public code.

3. **03 — Tailored Assessment**
   - Test the skills that actually matter for the role: generates role-specific technical assessments and interactive coding sandboxes derived directly from the job description with proctoring safeguards.

4. **04 — Explainable Job Match**
   - Understand why a candidate matches—or doesn't: evaluates candidates across 6 deterministic dimensions (0–100) with clear explanations of strengths, skill gaps, and evidence contradictions.

5. **05 — Recruiter Authority**
   - AI recommends; the recruiter decides: AI recommendations (`SHORTLIST`, `REVIEW`, `REJECT`) are strictly advisory. Recruiters retain sovereign override power with immutable audit trails.

2. **Star-Vanity Agnostic Deep Code Auditor**
   - Evaluates code architecture, test runner suites (`pytest`, `jest`), CI/CD workflows, and dependency hygiene without bias towards GitHub stars.

3. **Candidate Evidence Graph (DAG)**
   - Interactive directed acyclic graph mapping `Claim ➔ Skill ➔ Project ➔ Repository ➔ Code Commit ➔ Verdict`.

4. **Automated Technical Assessments**
   - 10, 20, 30, and 60-minute tailored coding challenges with automated rubric evaluation and instant code analysis.

5. **Evidence-Grounded AI Technical Interviewer**
   - Multi-turn technical interviews featuring dynamic probing questions grounded in the candidate's actual public GitHub commits.

6. **Candidate Side-by-Side Comparison**
   - 2 to 4 candidate matrix comparison with radar scores, trade-off breakdowns, and automated winner recommendations.

7. **Recruiter Copilot**
   - In-tenant conversational AI assistant for candidate discovery and skill verification queries.

8. **Recruitment Pipeline Kanban Board**
   - 6-stage drag-and-drop workflow (`Applied` ➔ `Screened` ➔ `Shortlisted` ➔ `Assessment` ➔ `Interview` ➔ `Hired`) with recruiter audit trails.

9. **Job Description Intelligence**
   - Automatic extraction of must-haves, nice-to-haves, seniority, and 4-tier candidate fit scoring.

10. **ATS Integration Layer**
    - Connectors and schema mapping for Greenhouse, Lever, and Workday.

11. **Recruitment Analytics & ROI Engine**
    - Real-time visibility into hours saved, cost savings, AI concordance rates (96.8%), and recruitment funnel conversion.

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Bajiyadav/Agentic.Ai.git
cd Agentic.Ai

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your database and API keys:
```bash
cp .env.example .env
```

Key configuration options:
- `DATABASE_URL`: PostgreSQL async connection string (`postgresql+asyncpg://...`)
- `OPENROUTER_API_KEY`: OpenRouter API key (intelligent mock fallback activates when placeholder is used)
- `GITHUB_TOKEN`: (Optional) GitHub PAT for higher API rate limits

### 3. Database Initialization & Migrations
```bash
# Apply Alembic migrations
alembic upgrade head
```

### 4. Run the Web Dashboard
```bash
python run_server.py
```
- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 5. Run via CLI
```bash
# Screen a candidate resume PDF (general audit)
python main.py --resume sample_resume.pdf

# Screen against company required skills & target role
python main.py --resume sample_resume.pdf --skills "Python, FastAPI, Docker, PostgreSQL" --role "Senior Backend Engineer" --min-exp 3.0

# Screen against a Job Description file (.txt or .md)
python main.py --resume sample_resume.pdf --jd path/to/job_description.txt

# Screen against a specific GitHub username override
python main.py --resume sample_resume.pdf --github octocat
```

---

## 🧪 Testing

Run the comprehensive test suite:
```bash
pytest tests/ -v
```

All 11 tests cover tenant isolation, file security, quota enforcement, background job workers, sovereign overrides, deep code auditing, and API endpoints.

---

## 🔒 Security & Compliance

- **Multi-Tenant Isolation**: Enforced at the database query level via tenant context and foreign keys.
- **Role-Based Access Control (RBAC)**: `owner`, `admin`, `recruiter`, `hiring_manager`, and `viewer`.
- **Tamper-Evident Audit Logging**: Immutable audit entries for every verdict, override, and state change.
- **Anti-Prompt-Injection Delimiters**: Strict separation of untrusted candidate input from agent instructions.
- **Encrypted Credentials**: AES-256 Fernet encryption for connected mailbox and integration credentials.

---

## 📄 License
MIT License.
