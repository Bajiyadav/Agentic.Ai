# 🤖 AuditAgent.ai — Enterprise AI Technical Hiring & Code Evidence Platform

> **Claim vs Evidence AI**: Auditing candidate resumes against verified public GitHub evidence, deep repository inspection, adaptive technical interviews, and automated rubric assessments.

AuditAgent.ai is a multi-tenant B2B technical recruitment platform designed to eliminate resume fluff, verify genuine engineering capabilities, and automate candidate evaluation.

---

## 🌟 Key Features & 11 Core Pillars

1. **Deterministic 40/30/30 Scoring Engine**
   - **40% Technical Skills Match**: Verified programming languages and frameworks vs resume claims.
   - **30% Code Quality & Practices**: Documentation ratio, original vs fork ratio, modularity, and testing presence.
   - **30% Timeline & Claim Consistency**: Commit velocity, activity timeline, and verifiable project impact.

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
# Screen a candidate resume PDF
python main.py --resume sample_resume.pdf

# Screen against a specific GitHub username
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
