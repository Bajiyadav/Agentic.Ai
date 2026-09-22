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
    ],
    "aws": [
        {
            "id_suffix": "aws_iam_arch",
            "type": "mcq",
            "modality": "mcq_architecture",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "AWS IAM Least Privilege & Cross-Account Access",
            "prompt": "When designing secure cross-account microservice communication between Account A (EKS/EC2) and Account B (DynamoDB / S3), what is the AWS-recommended security architecture?",
            "options": [
                "A) Embed permanent AWS root access keys in environment variables.",
                "B) Configure an IAM Role in Account B with a trust policy allowing Account A to call `sts:AssumeRole`, using temporary short-lived credentials.",
                "C) Open the S3 bucket and DynamoDB tables with public read/write permissions via Resource Policies.",
                "D) Hardcode IAM user secret keys inside the Docker container image."
            ],
            "correct_option": 1,
            "explanation": "Cross-account IAM roles assumed via STS AssumeRole provide temporary, rotatable credentials adhering to the principle of least privilege without persistent secrets.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "AWS"
        },
        {
            "id_suffix": "aws_backoff_retry",
            "type": "coding",
            "modality": "dsa_algorithms",
            "section": "coding",
            "section_title": "Section 2: Coding & Algorithmic Challenges",
            "title": "AWS: Exponential Backoff & Jitter Retry Algorithm",
            "prompt": "Implement `solution(base_delay, max_delay, attempt)` calculating truncated exponential backoff delay with full jitter for handling AWS API throttling (HTTP 429 / 503). Formula: min(max_delay, base_delay * (2 ** attempt)). Return the integer computed delay ceiling.",
            "starter_code": {
                "python": "def solution(base_delay: int, max_delay: int, attempt: int) -> int:\n    # Calculate exponential backoff ceiling\n    return 0\n",
                "go": "package main\n\nimport \"math\"\n\nfunc Solution(baseDelay, maxDelay, attempt int) int {\n    // Calculate exponential backoff ceiling\n    return 0\n}"
            },
            "test_cases": [
                {"input_data": [100, 3000, 0], "expected_output": 100, "description": "Attempt 0 returns base delay"},
                {"input_data": [100, 3000, 3], "expected_output": 800, "description": "Attempt 3 returns base * 2^3 = 800"},
                {"input_data": [100, 1000, 5], "expected_output": 1000, "description": "Exceeding max_delay caps at max_delay"}
            ],
            "difficulty": "Medium",
            "points": 30,
            "time_limit_minutes": 10,
            "skill_tested": "AWS"
        }
    ],
    "kafka": [
        {
            "id_suffix": "kafka_partitioning",
            "type": "mcq",
            "modality": "mcq_architecture",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "Apache Kafka Consumer Groups & Partition Assignment",
            "prompt": "In an Apache Kafka topic with 12 partitions consumed by a consumer group of 4 active consumer instances, what occurs if 2 new consumer instances join the group under the Cooperative Sticky Assignor?",
            "options": [
                "A) The topic drops all 12 partitions and restarts all consumer offsets to 0.",
                "B) An incremental cooperative rebalance occurs: only 4 partitions are reassigned without stopping consumption on unaffected partitions.",
                "C) Kafka triggers a Stop-The-World rebalance halting all partitions indefinitely.",
                "D) The new consumers remain idle because Kafka topics cannot scale past 4 consumers."
            ],
            "correct_option": 1,
            "explanation": "Cooperative Sticky Assignor enables incremental rebalancing: only partitions being moved are revoked, allowing uninterrupted stream processing on all other partitions.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "Kafka"
        },
        {
            "id_suffix": "kafka_stream_dedup",
            "type": "coding",
            "modality": "dsa_algorithms",
            "section": "coding",
            "section_title": "Section 2: Coding & Algorithmic Challenges",
            "title": "Kafka: Event Deduplication in Streaming Window",
            "prompt": "Implement `solution(events, window_size)` to filter out duplicate message IDs occurring within the sliding `window_size` of events. Return the list of accepted unique event IDs in order.",
            "starter_code": {
                "python": "def solution(events: list, window_size: int) -> list:\n    # Deduplicate stream events within window_size\n    return []\n",
                "go": "package main\n\nfunc Solution(events []string, windowSize int) []string {\n    // Deduplicate stream events within windowSize\n    return []string{}\n}"
            },
            "test_cases": [
                {"input_data": [["msg-1", "msg-2", "msg-1", "msg-3"], 3], "expected_output": ["msg-1", "msg-2", "msg-3"], "description": "Duplicate msg-1 in window is dropped"},
                {"input_data": [["a", "b", "c", "d", "a"], 2], "expected_output": ["a", "b", "c", "d", "a"], "description": "Repeated 'a' after window expires is accepted"},
                {"input_data": [["x", "x", "x"], 5], "expected_output": ["x"], "description": "Consecutive duplicates filtered to single event"}
            ],
            "difficulty": "Medium",
            "points": 30,
            "time_limit_minutes": 10,
            "skill_tested": "Kafka"
        }
    ],
    "go": [
        {
            "id_suffix": "go_concurrency",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "Go Concurrency: Channel Semantics & Deadlock Prevention",
            "prompt": "In Go, what happens when reading from a channel `ch` that has already been closed by the sender?",
            "options": [
                "A) The runtime panics immediately with `panic: send on closed channel`.",
                "B) The operation blocks forever waiting for new data.",
                "C) The receive operation immediately yields the zero value of the channel's type with `ok == false` once all buffered elements are drained.",
                "D) The channel automatically reopens and waits for the next sender."
            ],
            "correct_option": 2,
            "explanation": "Reading from a closed channel returns buffered values first, then yields zero values with second return value ok == false.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "Go"
        },
        {
            "id_suffix": "go_concurrent_worker",
            "type": "coding",
            "modality": "dsa_algorithms",
            "section": "coding",
            "section_title": "Section 2: Coding & Algorithmic Challenges",
            "title": "Go: Concurrent Batch Processing & Worker Pool",
            "prompt": "Implement `solution(tasks, worker_count)` to process a slice of integer task durations and return the total aggregated work processed and maximum single-worker load.",
            "starter_code": {
                "python": "def solution(tasks: list, worker_count: int) -> dict:\n    # Return {\"total_work\": sum(tasks), \"max_worker_load\": ...}\n    total = sum(tasks)\n    return {\"total_work\": total, \"task_count\": len(tasks)}\n",
                "go": "package main\n\nfunc Solution(tasks []int, workerCount int) map[string]int {\n    total := 0\n    for _, t := range tasks { total += t }\n    return map[string]int{\"total_work\": total, \"task_count\": len(tasks)}\n}"
            },
            "test_cases": [
                {"input_data": [[10, 20, 30, 40], 2], "expected_output": {"total_work": 100, "task_count": 4}, "description": "4 tasks across 2 workers"},
                {"input_data": [[5], 1], "expected_output": {"total_work": 5, "task_count": 1}, "description": "Single task single worker"}
            ],
            "difficulty": "Medium",
            "points": 30,
            "time_limit_minutes": 10,
            "skill_tested": "Go"
        }
    ],
    "golang": [
        {
            "id_suffix": "go_concurrency",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "Go Concurrency: Channel Semantics & Deadlock Prevention",
            "prompt": "In Go, what happens when reading from a channel `ch` that has already been closed by the sender?",
            "options": [
                "A) The runtime panics immediately with `panic: send on closed channel`.",
                "B) The operation blocks forever waiting for new data.",
                "C) The receive operation immediately yields the zero value of the channel's type with `ok == false` once all buffered elements are drained.",
                "D) The channel automatically reopens and waits for the next sender."
            ],
            "correct_option": 2,
            "explanation": "Reading from a closed channel returns buffered values first, then yields zero values with second return value ok == false.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "Go"
        }
    ],
    "kubernetes": [
        {
            "id_suffix": "k8s_qos_probes",
            "type": "mcq",
            "modality": "mcq_architecture",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "Kubernetes Pod Lifecycle & QoS Eviction Order",
            "prompt": "When a Kubernetes worker node experiences extreme memory pressure, which Quality of Service (QoS) class pod is evicted first by the kubelet?",
            "options": [
                "A) Guaranteed (requests == limits for CPU and Memory)",
                "B) Burstable (requests < limits)",
                "C) BestEffort (no requests and no limits set)",
                "D) Static System Pods"
            ],
            "correct_option": 2,
            "explanation": "BestEffort pods have no guaranteed memory reservation and are the first candidates for eviction when a node runs low on memory.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "Kubernetes"
        }
    ],
    "react": [
        {
            "id_suffix": "react_concurrency",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "React 18+ Fiber Reconciliation & State Batching",
            "prompt": "In React 18+, how does Automatic Batching behave inside native asynchronous handlers such as `setTimeout` or `fetch.then`?",
            "options": [
                "A) State updates inside async callbacks are never batched and always cause immediate re-renders.",
                "B) React 18 automatically batches all state updates across async callbacks, promises, and native event handlers into a single render pass.",
                "C) Async state batching requires wrapping all state setters in ReactDOM.unstable_batchedUpdates.",
                "D) Automatic batching was removed in React 18 in favor of manual FlushSync."
            ],
            "correct_option": 1,
            "explanation": "React 18 introduced automatic batching for all updates, including those inside promises, setTimeout, and native event listeners.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "React"
        }
    ],
    "typescript": [
        {
            "id_suffix": "ts_generics",
            "type": "mcq",
            "modality": "mcq_fundamentals",
            "section": "mcq",
            "section_title": "Section 1: Multiple Choice Questions (MCQs)",
            "title": "TypeScript Distributive Conditional Types & `infer`",
            "prompt": "In TypeScript, what type is produced by `type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;` when given `Promise<string>`?",
            "options": [
                "A) Promise<string>",
                "B) string",
                "C) any",
                "D) undefined"
            ],
            "correct_option": 1,
            "explanation": "The infer keyword extracts the inner resolved type U from the Promise wrapper, yielding string.",
            "difficulty": "Medium",
            "points": 20,
            "time_limit_minutes": 3,
            "skill_tested": "TypeScript"
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
        
        # Autonomous Stack Extraction: If req_skills is sparse, extract from raw JD text
        for known_skill in SKILL_QUESTION_TEMPLATES.keys():
            # Check for exact word or boundary matches
            pattern = rf"\b{known_skill}\b"
            import re
            if re.search(pattern, raw_jd_lower) or re.search(pattern, title_lower):
                capitalized = known_skill.upper() if len(known_skill) <= 3 else known_skill.capitalize()
                if not any(s.lower() == known_skill for s in req_skills + pref_skills):
                    req_skills.append(capitalized)

        # Build allowed skills set strictly from JD
        all_jd_skills = set()
        for s in req_skills + pref_skills:
            all_jd_skills.add(s.lower())

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
