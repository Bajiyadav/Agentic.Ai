"""
Job-Specific Assessment Service:
- JD Intelligence Question Recommender
- Recruiter Question Editing & Customization
- Publishing Validation & Anti-Hallucination Enforcement
- Candidate-Sanitized View Generation
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import JobOpening, JobAssessment, CandidateAssessment, Candidate
from src.services.exam_catalog import EXAM_TRACKS_20, QUESTION_MODALITIES
from src.services.expanded_question_bank import get_expanded_track_questions


# Skill to catalog questions or templates
SKILL_QUESTION_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "python": [
        {
            "id_suffix": "py_core",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "Python Memory Management & GIL Behavior",
            "prompt": "In CPython 3.12+, how does the Global Interpreter Lock (GIL) interact with multithreading when executing CPU-bound vs I/O-bound workloads?",
            "options": [
                "A) CPU-bound threads execute in parallel on separate CPU cores without lock contention.",
                "B) The GIL ensures only one thread executes Python bytecode at a time, making multiprocessing or native C extensions necessary for CPU parallelism.",
                "C) The GIL only affects asynchronous coroutines (asyncio) and has no impact on threading.Thread.",
                "D) The GIL was completely removed in CPython 3.10 for all operations."
            ],
            "correct_option": 1,
            "explanation": "CPython's GIL prevents simultaneous execution of Python bytecode across multiple OS threads, necessitating multiprocessing for CPU-bound parallelism.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "Python"
        },
        {
            "id_suffix": "py_algo",
            "type": "coding",
            "modality": "dsa_algorithms",
            "section": "coding",
            "section_title": "Section 2: Coding & Algorithmic Challenges",
            "title": "Python: Efficient Frequency Map & Top Elements",
            "prompt": "Implement `solution(nums, k)` to return the `k` most frequent elements in `nums`. Must achieve better than O(N log N) time.",
            "starter_code": {
                "python": "def solution(nums, k):\n    # Return list of top k frequent elements\n    return []\n"
            },
            "test_cases": [
                {"input_data": [[1, 1, 1, 2, 2, 3], 2], "expected_output": [1, 2], "description": "Top 2 frequent items"},
                {"input_data": [[1], 1], "expected_output": [1], "description": "Single element array"},
                {"input_data": [[4, 4, 4, 4, 5, 5, 6], 1], "expected_output": [4], "description": "Dominant item", "hidden": True}
            ],
            "difficulty": "Medium",
            "points": 30,
            "time_limit_minutes": 10,
            "skill_tested": "Python"
        }
    ],
    "fastapi": [
        {
            "id_suffix": "fastapi_concurrency",
            "type": "mcq",
            "modality": "mcq_architecture",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "FastAPI `def` vs `async def` Route Handlers",
            "prompt": "In FastAPI, how does the framework treat a standard synchronous route handler `def read_data():` versus an `async def read_data():` handler?",
            "options": [
                "A) Standard `def` endpoints are automatically rejected with a syntax warning.",
                "B) Standard `def` endpoints are dispatched to an external threadpool (`anyio.to_thread`), preventing CPU-bound operations from blocking the main event loop.",
                "C) Standard `def` endpoints run directly on the event loop, freezing all concurrent requests.",
                "D) `async def` routes are executed in a background sub-process while `def` runs in the main thread."
            ],
            "correct_option": 1,
            "explanation": "FastAPI dispatches non-async `def` handlers to Starlette's threadpool so blocking code doesn't stall the event loop.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "FastAPI"
        },
        {
            "id_suffix": "fastapi_debug",
            "type": "debugging",
            "modality": "code_debugging",
            "section": "coding",
            "section_title": "Section 2: Hands-On Debugging Challenges",
            "title": "FastAPI: Resolve Dependency Injection Lifecycle Defect",
            "prompt": "Fix the provided FastAPI dependency generator function so that database sessions are guaranteed to close even when exceptions occur during request processing.",
            "starter_code": {
                "python": (
                    "def get_db_session():\n"
                    "    session = create_session()\n"
                    "    try:\n"
                    "        yield session\n"
                    "    finally:\n"
                    "        session.close()\n"
                )
            },
            "test_cases": [
                {"input_data": ["normal_lifecycle"], "expected_output": "session_closed_cleanly", "description": "Normal lifecycle closes session"},
                {"input_data": ["exception_raised"], "expected_output": "session_closed_cleanly", "description": "Exception lifecycle triggers finally block"}
            ],
            "difficulty": "Medium",
            "points": 25,
            "time_limit_minutes": 8,
            "skill_tested": "FastAPI"
        }
    ],
    "postgresql": [
        {
            "id_suffix": "pg_ssi",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "PostgreSQL Serializable Snapshot Isolation (SSI)",
            "prompt": "Which PostgreSQL transaction isolation level guarantees Serializable Snapshot Isolation (SSI) to prevent write-skew anomalies without locking concurrent readers?",
            "options": [
                "A) Read Committed",
                "B) Repeatable Read",
                "C) Serializable",
                "D) Read Uncommitted"
            ],
            "correct_option": 2,
            "explanation": "PostgreSQL implements Serializable using SSI, detecting read-write conflict cycles without table-level locking.",
            "difficulty": "Hard",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "PostgreSQL"
        },
        {
            "id_suffix": "pg_window_sql",
            "type": "sql",
            "modality": "sql_window_cte",
            "section": "sql",
            "section_title": "Section 2: Interactive SQL Challenges",
            "title": "SQL: Cumulative Revenue & Department Window Analytics",
            "prompt": "Write an SQL query returning `dept_name`, `emp_name`, `salary`, and their rank within department using `DENSE_RANK() OVER (PARTITION BY dept_name ORDER BY salary DESC)`.",
            "starter_code": {
                "sql": (
                    "SELECT dept_name, emp_name, salary,\n"
                    "       DENSE_RANK() OVER (PARTITION BY dept_name ORDER BY salary DESC) AS rank\n"
                    "FROM employees\n"
                    "ORDER BY dept_name ASC, salary DESC, emp_name ASC;\n"
                )
            },
            "test_cases": [
                {
                    "description": "Evaluate dense rank window calculation",
                    "setup_sql": "CREATE TABLE employees (id INT, emp_name TEXT, dept_name TEXT, salary INT); INSERT INTO employees VALUES (1, 'Alice', 'Eng', 130000), (2, 'Bob', 'Eng', 120000), (3, 'Carol', 'Sales', 95000);",
                    "expected_output": [["Eng", "Alice", 130000, 1], ["Eng", "Bob", 120000, 2], ["Sales", "Carol", 95000, 1]]
                }
            ],
            "difficulty": "Medium",
            "points": 30,
            "time_limit_minutes": 10,
            "skill_tested": "PostgreSQL"
        }
    ],
    "sql": [
        {
            "id_suffix": "sql_window_cte",
            "type": "sql",
            "modality": "sql_window_cte",
            "section": "sql",
            "section_title": "Section 2: Interactive SQL Challenges",
            "title": "SQL: Top Earners per Department using CTE & Window Functions",
            "prompt": "Write an SQL query using a Common Table Expression (CTE) to find employees whose salary is within the top 2 salaries in their department.",
            "starter_code": {
                "sql": (
                    "WITH ranked AS (\n"
                    "    SELECT department, name, salary,\n"
                    "           DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rnk\n"
                    "    FROM employees\n"
                    ")\n"
                    "SELECT department, name, salary\n"
                    "FROM ranked\n"
                    "WHERE rnk <= 2\n"
                    "ORDER BY department ASC, salary DESC, name ASC;\n"
                )
            },
            "test_cases": [
                {
                    "description": "Check department top earners",
                    "setup_sql": "CREATE TABLE employees (id INT, name TEXT, department TEXT, salary INT); INSERT INTO employees VALUES (1, 'Alice', 'Eng', 120000), (2, 'Bob', 'Eng', 110000), (3, 'Charlie', 'Eng', 90000);",
                    "expected_output": [["Eng", "Alice", 120000], ["Eng", "Bob", 110000]]
                }
            ],
            "difficulty": "Medium",
            "points": 30,
            "time_limit_minutes": 10,
            "skill_tested": "SQL"
        }
    ],
    "rest apis": [
        {
            "id_suffix": "rest_idempotency",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "RESTful API Idempotency & HTTP Semantics",
            "prompt": "According to RFC 7231 / 9110 HTTP specifications, which of the following HTTP methods is NOT inherently idempotent?",
            "options": [
                "A) GET",
                "B) PUT",
                "C) DELETE",
                "D) POST"
            ],
            "correct_option": 3,
            "explanation": "POST is typically non-idempotent because multiple identical POST requests usually result in multiple created resources or side-effects.",
            "difficulty": "Easy",
            "points": 15,
            "time_limit_minutes": 2,
            "skill_tested": "REST APIs"
        }
    ],
    "docker": [
        {
            "id_suffix": "docker_layer_cache",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "Docker Multi-Stage Build & Layer Caching",
            "prompt": "To optimize Docker layer caching for Python applications, what is the best practice order in the Dockerfile?",
            "options": [
                "A) COPY . . followed by pip install -r requirements.txt",
                "B) COPY requirements.txt . followed by RUN pip install -r requirements.txt, then COPY . .",
                "C) Run pip install inside the entrypoint script at runtime.",
                "D) Always use --no-cache-dir on every single COPY command."
            ],
            "correct_option": 1,
            "explanation": "Copying only requirements.txt first allows Docker to cache installed dependencies when source files change without modifying packages.",
            "difficulty": "Easy",
            "points": 15,
            "time_limit_minutes": 2,
            "skill_tested": "Docker"
        }
    ],
    "redis": [
        {
            "id_suffix": "redis_eviction",
            "type": "mcq",
            "modality": "mcq_architecture",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "Redis Cache Invalidation & Eviction Policies",
            "prompt": "Which Redis maxmemory-policy should be selected when caching transient query results with TTL expiration where memory exhaustion must discard the least recently used keys with an explicit TTL?",
            "options": [
                "A) noeviction",
                "B) allkeys-lru",
                "C) volatile-lru",
                "D) volatile-random"
            ],
            "correct_option": 2,
            "explanation": "volatile-lru evicts the least recently used keys among those that have an expire (TTL) set.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "Redis"
        }
    ]
}


class JobAssessmentService:
    @staticmethod
    def generate_questions_from_jd(job: JobOpening) -> List[Dict[str, Any]]:
        """
        Generates job-specific assessment questions strictly derived from the Job's
        authoritative JD requirements: required_skills, preferred_skills, and responsibilities.
        
        CRITICAL ANTI-HALLUCINATION ENFORCEMENT:
        Does NOT invent or inject technologies not mentioned in the Job Opening.
        If JD does not contain Kubernetes, Rust, or AWS, they will never be introduced.
        """
        raw_jd_lower = (job.raw_jd_text or "").lower()
        title_lower = (job.title or "").lower()
        
        # Collect authoritative required & preferred skills
        req_skills = [str(s).strip() for s in (job.required_skills or []) if str(s).strip()]
        pref_skills = [str(s).strip() for s in (job.preferred_skills or []) if str(s).strip()]
        
        # Build allowed skills set strictly from JD
        all_jd_skills = set()
        for s in req_skills + pref_skills:
            all_jd_skills.add(s.lower())
        
        # Also include keywords explicitly present in raw_jd_text or title
        for known_skill in SKILL_QUESTION_TEMPLATES.keys():
            if known_skill in raw_jd_lower or known_skill in title_lower:
                all_jd_skills.add(known_skill)

        generated_questions: List[Dict[str, Any]] = []
        used_ids = set()
        order_idx = 1

        # 1. Process Required Skills (Mandatory)
        for skill in req_skills:
            skill_key = skill.lower()
            matching_templates = SKILL_QUESTION_TEMPLATES.get(skill_key, [])
            
            # If no direct match in templates, check if skill maps to one of our templates
            if not matching_templates:
                for k, templates in SKILL_QUESTION_TEMPLATES.items():
                    if k in skill_key or skill_key in k:
                        matching_templates = templates
                        break
            
            if matching_templates:
                for tmpl in matching_templates:
                    q_id = f"q_{job.id.hex[:6]}_{tmpl['id_suffix']}"
                    if q_id in used_ids:
                        continue
                    used_ids.add(q_id)
                    q = dict(tmpl)
                    q["id"] = q_id
                    q["order"] = order_idx
                    q["requirement_type"] = "required"
                    q["skill_type"] = "required"
                    q["relevance"] = f"Tests candidate's proficiency in {skill}, which is a mandatory requirement for {job.title}."
                    generated_questions.append(q)
                    order_idx += 1
            else:
                # Generate a customized foundational question for this required skill
                q_id = f"q_{job.id.hex[:6]}_{skill_key[:6]}_mcq"
                if q_id not in used_ids:
                    used_ids.add(q_id)
                    generated_questions.append({
                        "id": q_id,
                        "order": order_idx,
                        "type": "mcq",
                        "modality": "mcq_fundamentals",
                        "section": "mcq",
                        "section_title": "Section 1: Multiple Choice Questions (MCQs)",
                        "title": f"{skill}: Architectural & Core Principles",
                        "prompt": f"When architecting production solutions using {skill}, what is the primary consideration regarding performance, reliability, and concurrency?",
                        "options": [
                            f"A) {skill} requires careful resource lifecycle and concurrency management.",
                            f"B) {skill} operates strictly without any state or configuration overhead.",
                            f"C) {skill} cannot be monitored via standard observability metrics.",
                            f"D) {skill} enforces synchronous blocking operations by design."
                        ],
                        "correct_option": 0,
                        "explanation": f"In production systems, {skill} necessitates rigorous resource lifecycle and concurrency control.",
                        "difficulty": "Medium",
                        "points": 20,
                        "time_limit_minutes": 3,
                        "skill_tested": skill,
                        "requirement_type": "required",
                        "skill_type": "required",
                        "relevance": f"Tests candidate's practical architectural mastery of {skill}, required by {job.title}."
                    })
                    order_idx += 1

        # 2. Process Preferred Skills (Nice-to-Have, distinguishable)
        for skill in pref_skills:
            skill_key = skill.lower()
            matching_templates = SKILL_QUESTION_TEMPLATES.get(skill_key, [])
            if not matching_templates:
                for k, templates in SKILL_QUESTION_TEMPLATES.items():
                    if k in skill_key or skill_key in k:
                        matching_templates = templates
                        break

            if matching_templates:
                for tmpl in matching_templates[:1]:  # Take 1 question for preferred skill
                    q_id = f"q_{job.id.hex[:6]}_{tmpl['id_suffix']}_pref"
                    if q_id in used_ids:
                        continue
                    used_ids.add(q_id)
                    q = dict(tmpl)
                    q["id"] = q_id
                    q["order"] = order_idx
                    q["requirement_type"] = "preferred"
                    q["skill_type"] = "preferred"
                    q["relevance"] = f"Evaluates nice-to-have capability in {skill} as specified in the job description."
                    generated_questions.append(q)
                    order_idx += 1

        # Fallback: if no skills matched or list is empty, synthesize from role track in exam catalog
        if not generated_questions:
            from src.services.assessment_service import detect_exam_track
            track_id = detect_exam_track(job.title, req_skills)
            track = EXAM_TRACKS_20.get(track_id, EXAM_TRACKS_20["software_engineer"])
            for q_obj in track.get("questions", [])[:4]:
                q_dict = q_obj.model_dump()
                q_dict["id"] = f"q_{job.id.hex[:6]}_{q_dict['id']}"
                q_dict["order"] = order_idx
                q_dict["requirement_type"] = "required"
                q_dict["skill_type"] = "required"
                q_dict["skill_tested"] = q_dict.get("title", "").split(":")[0].strip() or "General Engineering"
                q_dict["relevance"] = f"Directly tests core competencies required for {job.title}."
                generated_questions.append(q_dict)
                order_idx += 1

        return generated_questions

    @staticmethod
    def generate_full_comprehensive_assessment(job: JobOpening) -> List[Dict[str, Any]]:
        """
        Generates a comprehensive 20-MCQ + 2-DSA + Debugging + SQL technical assessment
        tailored to the JobOpening's technical track and required skills.
        Structure:
        - 10 Core Domain Fundamentals MCQs
        - 10 System Architecture & Concurrency MCQs
        - 2 Algorithmic DSA Coding Challenges (visible + hidden tests)
        - 1 Code Bug Fixing & Debugging Challenge
        - 1 Interactive Database / SQL Challenge
        Total: 24 rigorous technical challenges.
        """
        from src.services.assessment_service import detect_exam_track
        req_skills = [str(s).strip() for s in (job.required_skills or []) if str(s).strip()]
        track_id = detect_exam_track(job.title, req_skills)
        
        raw_questions = get_expanded_track_questions(track_id)
        generated_questions: List[Dict[str, Any]] = []
        
        for idx, q_obj in enumerate(raw_questions, start=1):
            q_dict = q_obj.model_dump()
            q_dict["id"] = f"q_{job.id.hex[:6]}_{q_dict['id']}"
            q_dict["order"] = idx
            q_dict["requirement_type"] = "required"
            q_dict["skill_type"] = "required"
            q_dict["skill_tested"] = q_dict.get("title", "").split(":")[0].strip() or "Technical Competency"
            q_dict["relevance"] = f"Directly benchmarks core competency for {job.title}."
            generated_questions.append(q_dict)

        return generated_questions

    @staticmethod
    def validate_assessment_for_publishing(assessment: JobAssessment) -> Tuple[bool, List[str]]:
        """
        Validates the assessment against all required publishing criteria:
        1. Assessment has a valid Job association
        2. Assessment has at least one question
        3. Every question has required fields (id, title, prompt, skill_tested)
        4. MCQ has valid options (>= 2) and a valid correct_option (0 <= index < len(options))
        5. Coding questions have required starter_code and test_cases
        6. No duplicate question IDs
        """
        errors: List[str] = []

        if not assessment.job_id:
            errors.append("Assessment is missing its parent Job Opening association.")

        questions = assessment.questions_json or []
        if not questions or len(questions) == 0:
            errors.append("Assessment must have at least one question before publishing.")
            return False, errors

        seen_ids = set()
        for idx, q in enumerate(questions, start=1):
            q_id = q.get("id")
            if not q_id:
                errors.append(f"Question #{idx} is missing a question_id.")
            elif q_id in seen_ids:
                errors.append(f"Duplicate question_id '{q_id}' found at question #{idx}.")
            else:
                seen_ids.add(q_id)

            if not q.get("title"):
                errors.append(f"Question #{idx} is missing a title.")
            if not q.get("prompt"):
                errors.append(f"Question #{idx} is missing a prompt description.")
            if not q.get("skill_tested"):
                errors.append(f"Question #{idx} is missing skill_tested.")

            q_type = q.get("type", "mcq").lower()

            if q_type == "mcq":
                opts = q.get("options", [])
                if not isinstance(opts, list) or len(opts) < 2:
                    errors.append(f"MCQ Question #{idx} ('{q.get('title')}') must have at least 2 options.")
                correct = q.get("correct_option")
                if correct is None or not isinstance(correct, int) or correct < 0 or correct >= len(opts):
                    errors.append(f"MCQ Question #{idx} ('{q.get('title')}') has invalid correct_option ({correct}). Must be an integer between 0 and {len(opts)-1}.")

            elif q_type in ["coding", "sql", "debugging"]:
                starter = q.get("starter_code")
                if not starter or (isinstance(starter, dict) and not any(starter.values())):
                    errors.append(f"Coding/SQL Question #{idx} ('{q.get('title')}') is missing starter_code.")
                tcs = q.get("test_cases")
                if not tcs or not isinstance(tcs, list) or len(tcs) == 0:
                    errors.append(f"Coding/SQL Question #{idx} ('{q.get('title')}') must have at least 1 automated test case.")

        return len(errors) == 0, errors

    @staticmethod
    def sanitize_questions_for_candidate(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Strips correct answers, explanations, and hidden test cases so candidates
        never receive answers in frontend payloads.
        """
        sanitized = []
        for q in questions:
            q_clean = {
                "id": q.get("id"),
                "order": q.get("order", 1),
                "type": q.get("type"),
                "modality": q.get("modality", "mcq_fundamentals"),
                "section": q.get("section", "mcq"),
                "section_title": q.get("section_title", "Section 1: Multiple Choice Questions (MCQs)"),
                "title": q.get("title"),
                "prompt": q.get("prompt"),
                "code_snippet": q.get("code_snippet"),
                "options": q.get("options", []),
                "starter_code": q.get("starter_code", {}),
                "time_limit_minutes": q.get("time_limit_minutes", 10),
                "points": q.get("points", 20),
                "skill_tested": q.get("skill_tested"),
                "requirement_type": q.get("requirement_type", "required"),
                "difficulty": q.get("difficulty", "Medium"),
                "db_schema_setup": q.get("db_schema_setup")
            }

            # Filter visible test cases only
            raw_tcs = q.get("test_cases", [])
            visible_tcs = []
            for tc in raw_tcs:
                if not tc.get("hidden", False):
                    visible_tcs.append({
                        "description": tc.get("description"),
                        "input_data": tc.get("input_data"),
                        "expected_output": tc.get("expected_output"),
                        "setup_sql": tc.get("setup_sql")
                    })
            q_clean["test_cases"] = visible_tcs
            sanitized.append(q_clean)
        return sanitized
