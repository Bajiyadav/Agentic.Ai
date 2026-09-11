"""
Comprehensive 20 Role-Specific Exam Catalog with 5 Challenge Types Per Role
and 10 Question Modalities for Deep Customization.

Challenge Types in Every Exam:
1. Multiple Choice Questions (MCQ - Core Concepts)
2. Multiple Choice Questions (MCQ - System Architecture)
3. Algorithmic Coding & DSA Challenge
4. Interactive SQL / Database Challenge (Evaluated in SQLite in-memory sandbox)
5. Code Bug Fixing & Debugging / Security Challenge

10 Customizable Question Modalities:
1. mcq_fundamentals: Core Domain Fundamentals & Protocols
2. mcq_architecture: System Architecture & Distributed Trade-offs
3. dsa_algorithms: Algorithmic Data Structures & Complexity
4. sql_window_cte: SQL Window Functions & CTEs
5. sql_aggregation_analytics: SQL Grouping, Aggregations & Business Metrics
6. code_debugging: Bug Hunting & Concurrency/Memory Remediation
7. security_audit: Security Vulnerability Detection & Input Sanitization
8. performance_optimization: Latency, Caching & Memory Profiling
9. resilience_fault_tolerance: Exponential Backoff, Circuit Breaker & Retry Loops
10. data_transformation: Pipeline ETL, Normalization & Schema Validation
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AssessmentQuestion(BaseModel):
    id: str
    type: str  # mcq, coding, debugging, sql, security, architecture
    modality: str = "mcq_fundamentals"  # 1 of the 10 modalities
    section: str = "mcq"  # "mcq", "coding", "sql"
    section_title: str = "Section 1: Multiple Choice Questions (MCQs)"
    title: str
    prompt: str
    code_snippet: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    correct_option: Optional[int] = None
    explanation: Optional[str] = None
    starter_code: Dict[str, str] = Field(default_factory=dict)
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)
    expected_topics: List[str] = Field(default_factory=list)
    time_limit_minutes: int = 5
    db_schema_setup: Optional[str] = None


QUESTION_MODALITIES = [
    {"id": "mcq_fundamentals", "label": "Core Domain Fundamentals", "icon": "📘", "desc": "Foundational protocol and language specifications"},
    {"id": "mcq_architecture", "label": "System Architecture & Design", "icon": "🏛️", "desc": "High-level trade-offs, scaling and distributed topologies"},
    {"id": "dsa_algorithms", "label": "Data Structures & DSA", "icon": "💻", "desc": "Time/space complexity, hash maps, two pointers, tree traversals"},
    {"id": "sql_window_cte", "label": "SQL Window Functions & CTEs", "icon": "🗄️", "desc": "DENSE_RANK(), LAG(), LEAD(), PARTITION BY and recursive CTEs"},
    {"id": "sql_aggregation_analytics", "label": "SQL Analytics & Aggregation", "icon": "📊", "desc": "GROUP BY, HAVING, CASE WHEN and business KPI metrics"},
    {"id": "code_debugging", "label": "Code Bug Fixing & Debugging", "icon": "🐛", "desc": "Locating and remediating subtle runtime defects and edge cases"},
    {"id": "security_audit", "label": "Security Audit & Sanitization", "icon": "🛡️", "desc": "OWASP Top 10, injection defense, timing attacks, sanitizers"},
    {"id": "performance_optimization", "label": "Caching & Memory Profiling", "icon": "⚡", "desc": "LRU caches, memory leak prevention, retain cycles"},
    {"id": "resilience_fault_tolerance", "label": "Resilience & Retry Policies", "icon": "🔄", "desc": "Exponential backoff with jitter, circuit breakers, rate limiters"},
    {"id": "data_transformation", "label": "Data Transformation & ETL", "icon": "🔀", "desc": "Stream deduplication, parameter canonicalization, schema assertions"}
]


# =======================================================================
# 20 ROLE-SPECIFIC EXAM TRACKS
# =======================================================================

EXAM_TRACKS_20: Dict[str, Dict[str, Any]] = {
    # 1. SOFTWARE ENGINEER
    "software_engineer": {
        "track_id": "software_engineer",
        "title": "Software Engineer (Backend & DSA)",
        "badge": "DSA & Concurrency",
        "description": "Evaluates PostgreSQL SSI isolation, async event loop blocking, sliding window rate limiters, SQL employee salary rankings, and Two Sum.",
        "skills": ["Python", "Algorithms", "AsyncIO", "FastAPI", "PostgreSQL", "SQL"],
        "questions": [
            AssessmentQuestion(
                id="swe_mcq_1",
                type="mcq",
                modality="mcq_fundamentals",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="PostgreSQL Transaction Isolation & SSI",
                prompt="Which transaction isolation level guarantees Serializable Snapshot Isolation (SSI) to prevent write-skew anomalies without blocking readers?",
                options=["A) Read Committed", "B) Repeatable Read", "C) Serializable", "D) Read Uncommitted"],
                correct_option=2,
                explanation="PostgreSQL implements Serializable using SSI, detecting read-write conflict cycles without locking tables.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="swe_mcq_2",
                type="mcq",
                modality="mcq_architecture",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Async Event Loop & CPU Blocking",
                prompt="In an asynchronous Python service (FastAPI/asyncio), what occurs if a CPU-heavy computation or blocking `time.sleep(5)` is executed directly inside an `async def` handler?",
                options=[
                    "A) The runtime yields execution to other awaiting coroutines.",
                    "B) The entire event loop thread is frozen, blocking all concurrent requests for 5 seconds.",
                    "C) The OS automatically offloads the computation to a worker thread.",
                    "D) A ConcurrencyViolationError is raised immediately."
                ],
                correct_option=1,
                explanation="In single-threaded event loop models, synchronous blocking halts the loop thread, starving all concurrent tasks.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="swe_dsa_1",
                type="coding",
                modality="dsa_algorithms",
                section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="DSA: Two Sum Target Pair Finder (O(N) Time)",
                prompt="Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`. Must run in O(N) time.",
                starter_code={
                    "python": (
                        "def solution(nums, target):\n"
                        "    seen = {}\n"
                        "    for i, num in enumerate(nums):\n"
                        "        comp = target - num\n"
                        "        if comp in seen:\n"
                        "            return [seen[comp], i]\n"
                        "        seen[num] = i\n"
                        "    return []\n"
                    )
                },
                test_cases=[{"input_data": [[2, 7, 11, 15], 9], "expected_output": [0, 1], "description": "Classic two sum"}],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="swe_sql_1",
                type="sql",
                modality="sql_window_cte",
                section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Top Paid Employees per Department with DENSE_RANK()",
                prompt="Write an SQL query to select `department`, `name`, `salary` for employees with rank <= 2 in each department ordered by `department` ASC, `salary` DESC.",
                starter_code={
                    "sql": (
                        "WITH ranked AS (\n"
                        "    SELECT department, name, salary,\n"
                        "           DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) as rank\n"
                        "    FROM employees\n"
                        ")\n"
                        "SELECT department, name, salary\n"
                        "FROM ranked\n"
                        "WHERE rank <= 2\n"
                        "ORDER BY department ASC, salary DESC, name ASC;\n"
                    )
                },
                test_cases=[{
                    "description": "Top earners per dept",
                    "setup_sql": "CREATE TABLE employees (id INT, name TEXT, department TEXT, salary INT); INSERT INTO employees VALUES (1, 'Alice', 'Eng', 120000), (2, 'Bob', 'Eng', 110000), (3, 'Charlie', 'Eng', 90000);",
                    "expected_output": [["Eng", "Alice", 120000], ["Eng", "Bob", 110000]]
                }],
                time_limit_minutes=10
            ),
            AssessmentQuestion(
                id="swe_deb_1",
                type="debugging",
                modality="code_debugging",
                section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Sliding Window Rate Limiter Request Timestamp Leak",
                prompt="Fix the sliding window rate limiter function so expired timestamps older than `window_sec` are evicted before checking threshold.",
                starter_code={
                    "python": (
                        "def solution(timestamps, max_requests, window_sec):\n"
                        "    # Return list of booleans: True if request allowed, False if throttled\n"
                        "    allowed = []\n"
                        "    q = []\n"
                        "    for t in timestamps:\n"
                        "        while q and q[0] <= t - window_sec:\n"
                        "            q.pop(0)\n"
                        "        if len(q) < max_requests:\n"
                        "            q.append(t)\n"
                        "            allowed.append(True)\n"
                        "        else:\n"
                        "            allowed.append(False)\n"
                        "    return allowed\n"
                    )
                },
                test_cases=[{"input_data": [[1, 2, 3, 11, 12], 2, 10], "expected_output": [True, True, False, True, True], "description": "Rate limit window eviction"}],
                time_limit_minutes=8
            )
        ]
    },

    # 2. DATA ENGINEER
    "data_engineer": {
        "track_id": "data_engineer",
        "title": "Data Engineer (SQL & Data Pipelines)",
        "badge": "SQL & Data Pipeline",
        "description": "Evaluates columnar formats, distributed partition skew, advanced SQL window functions, and streaming deduplication.",
        "skills": ["SQL", "Python", "Data Modeling", "ETL", "Parquet", "Spark"],
        "questions": [
            AssessmentQuestion(
                id="de_mcq_1",
                type="mcq",
                modality="mcq_fundamentals",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Columnar Storage & Parquet Efficiency",
                prompt="Why does Apache Parquet provide orders of magnitude higher compression and scan speed for analytical queries compared to CSV?",
                options=[
                    "A) Parquet compiles SQL into machine bytecode.",
                    "B) Values in the same column have uniform data types and are stored contiguously, allowing run-length encoding and column projection skipping.",
                    "C) Parquet automatically deletes duplicate records upon ingestion.",
                    "D) Parquet replaces relational joins with NoSQL key-value lookups."
                ],
                correct_option=1,
                explanation="Columnar layouts group similar values together for superior compression and skip unreferenced columns entirely during query projection.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="de_mcq_2",
                type="mcq",
                modality="mcq_architecture",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Distributed Data Partitioning & Skew Remediation",
                prompt="When running a large distributed join in Spark or BigQuery, what is the primary symptom of severe 'Data Skew'?",
                options=[
                    "A) Immediate memory exhaustion on driver node during query planning.",
                    "B) 99% of tasks finish in seconds, while 1 single task hangs for hours processing a high-cardinality hot key (e.g. NULL or 'DEFAULT').",
                    "C) Total loss of table metadata in metastore.",
                    "D) An instant NetworkTimeoutException."
                ],
                correct_option=1,
                explanation="Data skew causes an uneven distribution of records to reducers, leading to the dreaded straggler task bottleneck.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="de_dsa_1",
                type="coding",
                modality="dsa_algorithms",
                section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Pipeline: Event Stream Deduplication & Aggregator",
                prompt="Implement a streaming deduplicator function `solution(events, window_sec)` that suppresses duplicate events for a user within `window_sec`.",
                starter_code={
                    "python": (
                        "def solution(events, window_sec):\n"
                        "    last_seen = {}\n"
                        "    counts = {}\n"
                        "    for ev in events:\n"
                        "        key = (ev['user_id'], ev['type'])\n"
                        "        ts = ev['timestamp']\n"
                        "        if key not in last_seen or ts - last_seen[key] > window_sec:\n"
                        "            last_seen[key] = ts\n"
                        "            counts[ev['type']] = counts.get(ev['type'], 0) + 1\n"
                        "    return counts\n"
                    )
                },
                test_cases=[{
                    "input_data": [
                        [
                            {"id": "1", "user_id": "u1", "type": "click", "timestamp": 10},
                            {"id": "2", "user_id": "u1", "type": "click", "timestamp": 12},
                            {"id": "3", "user_id": "u1", "type": "view", "timestamp": 13},
                            {"id": "4", "user_id": "u2", "type": "click", "timestamp": 14},
                            {"id": "5", "user_id": "u1", "type": "click", "timestamp": 20}
                        ],
                        5
                    ],
                    "expected_output": {"click": 3, "view": 1},
                    "description": "Deduplicate rapid clicks from u1 within 5s window"
                }],
                time_limit_minutes=10
            ),
            AssessmentQuestion(
                id="de_sql_1",
                type="sql",
                modality="sql_window_cte",
                section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Department Salary Ranking via Window Functions",
                prompt="Write an SQL query to calculate the salary rank of employees within each department using `DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) as rank`. Filter rank <= 2.",
                starter_code={
                    "sql": (
                        "-- Write your SQL query below\n"
                        "WITH ranked AS (\n"
                        "    SELECT department, name, salary,\n"
                        "           DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) as rank\n"
                        "    FROM employees\n"
                        ")\n"
                        "SELECT department, name, salary, rank\n"
                        "FROM ranked\n"
                        "WHERE rank <= 2\n"
                        "ORDER BY department ASC, salary DESC, name ASC;\n"
                    )
                },
                test_cases=[{
                    "description": "Top 2 earners per department with tie handling",
                    "setup_sql": (
                        "CREATE TABLE employees (id INT, name TEXT, department TEXT, salary INT);\n"
                        "INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 130000);\n"
                        "INSERT INTO employees VALUES (2, 'Bob', 'Engineering', 120000);\n"
                        "INSERT INTO employees VALUES (3, 'Charlie', 'Engineering', 120000);\n"
                        "INSERT INTO employees VALUES (4, 'Dan', 'Engineering', 100000);\n"
                        "INSERT INTO employees VALUES (5, 'Emma', 'Sales', 95000);\n"
                        "INSERT INTO employees VALUES (6, 'Frank', 'Sales', 90000);\n"
                        "INSERT INTO employees VALUES (7, 'Grace', 'Sales', 80000);\n"
                    ),
                    "expected_output": [
                        ["Engineering", "Alice", 130000, 1],
                        ["Engineering", "Bob", 120000, 2],
                        ["Engineering", "Charlie", 120000, 2],
                        ["Sales", "Emma", 95000, 1],
                        ["Sales", "Frank", 90000, 2]
                    ]
                }],
                time_limit_minutes=12
            ),
            AssessmentQuestion(
                id="de_deb_1",
                type="debugging",
                modality="code_debugging",
                section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Data Pipeline Batch Chunk Size Overflow",
                prompt="The starter function chunks records into batches of size `batch_size`. A bug drops the trailing partial batch. Fix it to include all records.",
                starter_code={
                    "python": (
                        "def solution(records, batch_size):\n"
                        "    # Partition records into batches\n"
                        "    batches = []\n"
                        "    for i in range(0, len(records), batch_size):\n"
                        "        batches.append(records[i:i + batch_size])\n"
                        "    return batches\n"
                    )
                },
                test_cases=[{"input_data": [[1, 2, 3, 4, 5], 2], "expected_output": [[1, 2], [3, 4], [5]], "description": "Include trailing partial batch"}],
                time_limit_minutes=8
            )
        ]
    },

    # 3. FRONTEND ENGINEER
    "frontend_engineer": {
        "track_id": "frontend_engineer",
        "title": "Frontend Engineer (JavaScript & Systems)",
        "badge": "UI & JavaScript DSA",
        "description": "Evaluates React reconciliation, browser microtasks, Core Web Vitals, debounce algorithms, DOM tree traversal, and state query tables.",
        "skills": ["JavaScript", "React", "TypeScript", "HTML/CSS", "Web Performance", "SQL"],
        "questions": [
            AssessmentQuestion(
                id="fe_mcq_1",
                type="mcq",
                modality="mcq_fundamentals",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="React Reconciliation & Fiber Architecture",
                prompt="What is the primary architectural advantage of React's Fiber reconciler compared to the legacy stack reconciler?",
                options=[
                    "A) Fiber compiles JSX directly into native C++ WebAssembly binaries.",
                    "B) Fiber splits rendering work into incremental units, allowing the browser to pause and prioritize high-priority user interactions.",
                    "C) Fiber eliminates the need for virtual DOM diffing entirely.",
                    "D) Fiber enforces synchronous rendering without requestIdleCallback."
                ],
                correct_option=1,
                explanation="React Fiber enables cooperative multitasking, breaking reconciliation into interruptible units of work based on priority lanes.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="fe_mcq_2",
                type="mcq",
                modality="mcq_architecture",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Event Loop Microtask Execution Order",
                prompt="In the browser JavaScript runtime, in what exact order are Promises, `requestAnimationFrame`, and `setTimeout(fn, 0)` callbacks executed after the current synchronous script completes?",
                options=[
                    "A) `setTimeout` -> Microtasks (Promises) -> `requestAnimationFrame`",
                    "B) Microtasks (Promises) -> `requestAnimationFrame` (before paint) -> `setTimeout` (Macrotask in next loop)",
                    "C) `requestAnimationFrame` -> `setTimeout` -> Microtasks",
                    "D) They execute concurrently across multiple CPU threads."
                ],
                correct_option=1,
                explanation="Microtasks drain immediately after synchronous execution. Rendering callbacks (rAF) run before paint, and macrotasks (setTimeout) run on subsequent loop iterations.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="fe_dsa_1",
                type="coding",
                modality="dsa_algorithms",
                section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Frontend DSA: DOM Tree Deep Path Finder (DFS)",
                prompt="Given a nested DOM-like tree object and a target node `id`, find and return the path of IDs from root to target. Return empty list if not found.",
                starter_code={
                    "python": (
                        "def solution(tree, target_id):\n"
                        "    def dfs(node, path):\n"
                        "        if node['id'] == target_id:\n"
                        "            return path + [node['id']]\n"
                        "        for child in node.get('children', []):\n"
                        "            res = dfs(child, path + [node['id']])\n"
                        "            if res:\n"
                        "                return res\n"
                        "        return None\n"
                        "    return dfs(tree, []) or []\n"
                    )
                },
                test_cases=[{
                    "input_data": [
                        {"id": "app", "children": [{"id": "main", "children": [{"id": "btn", "children": []}]}]},
                        "btn"
                    ],
                    "expected_output": ["app", "main", "btn"],
                    "description": "Find path to button"
                }],
                time_limit_minutes=10
            ),
            AssessmentQuestion(
                id="fe_sql_1",
                type="sql",
                modality="sql_aggregation_analytics",
                section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Core Web Vitals LCP Performance Report",
                prompt="Write an SQL query to calculate the average Largest Contentful Paint (LCP) and 75th percentile status ('GOOD' if avg_lcp <= 2500 else 'POOR') grouped by device type.",
                starter_code={
                    "sql": (
                        "SELECT device,\n"
                        "       ROUND(AVG(lcp_ms), 1) as avg_lcp,\n"
                        "       CASE WHEN AVG(lcp_ms) <= 2500 THEN 'GOOD' ELSE 'POOR' END as lcp_status\n"
                        "FROM web_vitals\n"
                        "GROUP BY device\n"
                        "ORDER BY device ASC;\n"
                    )
                },
                test_cases=[{
                    "description": "Calculate average LCP per device",
                    "setup_sql": "CREATE TABLE web_vitals (id INT, device TEXT, lcp_ms INT); INSERT INTO web_vitals VALUES (1, 'mobile', 2600), (2, 'mobile', 2800), (3, 'desktop', 1800), (4, 'desktop', 2100);",
                    "expected_output": [["desktop", 1950.0, "GOOD"], ["mobile", 2700.0, "POOR"]]
                }],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="fe_deb_1",
                type="debugging",
                modality="code_debugging",
                section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Debounce Timer Cancellation Leak",
                prompt="The starter debounce function fails to cancel previously scheduled timer when rapid calls arrive. Fix the timer clearing logic.",
                starter_code={
                    "python": (
                        "def solution(calls_ms, delay_ms):\n"
                        "    # calls_ms: sorted list of call timestamps\n"
                        "    # Only call that has no subsequent call within delay_ms should fire\n"
                        "    fired = []\n"
                        "    for i in range(len(calls_ms)):\n"
                        "        is_last = (i == len(calls_ms) - 1)\n"
                        "        if is_last or (calls_ms[i+1] - calls_ms[i] > delay_ms):\n"
                        "            fired.append(calls_ms[i] + delay_ms)\n"
                        "    return fired\n"
                    )
                },
                test_cases=[{"input_data": [[10, 20, 30, 100], 50], "expected_output": [80, 150], "description": "Debounce trailing edge fires at 80 and 150"}],
                time_limit_minutes=8
            )
        ]
    },

    # 4. AI & ML ENGINEER
    "ml_engineer": {
        "track_id": "ml_engineer",
        "title": "AI & Machine Learning Engineer (Math & Vectors)",
        "badge": "Vectors & Deep Learning",
        "description": "Evaluates transformer self-attention, cross-entropy, vector cosine similarity top-k search, model inference latency SQL, and gradient descent.",
        "skills": ["Python", "PyTorch", "NumPy", "Transformers", "Linear Algebra", "SQL"],
        "questions": [
            AssessmentQuestion(
                id="ml_mcq_1",
                type="mcq",
                modality="mcq_fundamentals",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Transformer Scaled Dot-Product Attention",
                prompt="In the Transformer equation Attention(Q, K, V) = softmax((Q * K^T) / sqrt(d_k)) * V, why is the dot product scaled by 1 / sqrt(d_k)?",
                options=[
                    "A) To ensure the output vectors sum to zero.",
                    "B) For large values of d_k, dot products grow large in magnitude, pushing softmax into regions with extremely small gradients (vanishing gradients).",
                    "C) To convert dot products from Cartesian coordinates to spherical coordinates.",
                    "D) It reduces the memory complexity of matrix multiplication from O(N^2) to O(N)."
                ],
                correct_option=1,
                explanation="Scaling by 1/sqrt(d_k) prevents dot products from growing excessively large, keeping softmax gradients stable during backpropagation.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="ml_mcq_2",
                type="mcq",
                modality="mcq_architecture",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Loss Functions: Cross-Entropy vs Mean Squared Error",
                prompt="Why is Cross-Entropy Loss strongly preferred over Mean Squared Error (MSE) when training neural network classification models with Softmax outputs?",
                options=[
                    "A) MSE cannot be computed for multi-dimensional tensors.",
                    "B) When combined with Softmax, MSE leads to vanishing gradient plateaus for confident incorrect predictions, whereas Cross-Entropy yields a steep linear error gradient.",
                    "C) Cross-Entropy is strictly convex while MSE is always non-differentiable.",
                    "D) MSE requires GPU hardware floating point registers."
                ],
                correct_option=1,
                explanation="The derivative of Cross-Entropy with Softmax simplifies directly to (y_hat - y), avoiding saturation plateaus that stall MSE.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="ml_dsa_1",
                type="coding",
                modality="dsa_algorithms",
                section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Vectors: Cosine Similarity Top-K Nearest Neighbors",
                prompt="Given a query vector `q` and a list of candidate vectors with IDs `candidates`, compute cosine similarity and return top-k nearest candidate IDs.",
                starter_code={
                    "python": (
                        "import math\n\n"
                        "def solution(query, candidates, k):\n"
                        "    def cosine_sim(v1, v2):\n"
                        "        dot = sum(a * b for a, b in zip(v1, v2))\n"
                        "        norm1 = math.sqrt(sum(a * a for a in v1))\n"
                        "        norm2 = math.sqrt(sum(b * b for b in v2))\n"
                        "        if norm1 == 0 or norm2 == 0:\n"
                        "            return 0.0\n"
                        "        return dot / (norm1 * norm2)\n\n"
                        "    scored = []\n"
                        "    for cid, vec in candidates:\n"
                        "        sim = cosine_sim(query, vec)\n"
                        "        scored.append((sim, cid))\n"
                        "    scored.sort(key=lambda x: (-x[0], x[1]))\n"
                        "    return [cid for _, cid in scored[:k]]\n"
                    )
                },
                test_cases=[{
                    "input_data": [
                        [1.0, 0.0],
                        [["doc1", [1.0, 0.0]], ["doc2", [0.0, 1.0]], ["doc3", [0.8, 0.2]]],
                        2
                    ],
                    "expected_output": ["doc1", "doc3"],
                    "description": "Top 2 most similar vectors"
                }],
                time_limit_minutes=10
            ),
            AssessmentQuestion(
                id="ml_sql_1",
                type="sql",
                modality="sql_aggregation_analytics",
                section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Model Inference p90 Latency Benchmark",
                prompt="Write an SQL query to calculate the average latency and total inference count per model name from `model_metrics`. Order by total count DESC.",
                starter_code={
                    "sql": (
                        "SELECT model_name,\n"
                        "       COUNT(*) as total_inferences,\n"
                        "       ROUND(AVG(latency_ms), 1) as avg_latency\n"
                        "FROM model_metrics\n"
                        "GROUP BY model_name\n"
                        "ORDER BY total_inferences DESC;\n"
                    )
                },
                test_cases=[{
                    "description": "Aggregate model latency",
                    "setup_sql": "CREATE TABLE model_metrics (id INT, model_name TEXT, latency_ms INT); INSERT INTO model_metrics VALUES (1, 'gemini-flash', 120), (2, 'gemini-flash', 140), (3, 'claude-3', 250);",
                    "expected_output": [["gemini-flash", 2, 130.0], ["claude-3", 1, 250.0]]
                }],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="ml_deb_1",
                type="debugging",
                modality="code_debugging",
                section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Gradient Descent Weight Update Sign Error",
                prompt="The starter gradient descent update function mistakenly adds the gradient instead of subtracting it. Fix the update formula: `w = w - lr * grad`.",
                starter_code={
                    "python": (
                        "def solution(weights, gradients, learning_rate):\n"
                        "    # Perform SGD weight update: w = w - lr * grad\n"
                        "    updated = []\n"
                        "    for w, g in zip(weights, gradients):\n"
                        "        updated.append(round(w - learning_rate * g, 4))\n"
                        "    return updated\n"
                    )
                },
                test_cases=[{"input_data": [[0.5, -0.2], [0.1, -0.4], 0.1], "expected_output": [0.49, -0.16], "description": "Update weights via gradient descent"}],
                time_limit_minutes=8
            )
        ]
    },

    # 5. DEVOPS & SRE
    "devops_sre": {
        "track_id": "devops_sre",
        "title": "DevOps & Cloud SRE (Infrastructure & Systems)",
        "badge": "Systems & Reliability",
        "description": "Evaluates Kubernetes pod lifecycles, CIDR subnets, canary deployments, access log latency parsers, and exponential backoff.",
        "skills": ["Kubernetes", "Docker", "Linux", "CI/CD", "Python", "Prometheus", "SQL"],
        "questions": [
            AssessmentQuestion(
                id="ops_mcq_1",
                type="mcq",
                modality="mcq_fundamentals",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Kubernetes Pod CrashLoopBackOff Diagnosis",
                prompt="What is the most direct command to retrieve the previous terminated container's exit code and logs when a Pod is stuck in CrashLoopBackOff?",
                options=[
                    "A) `kubectl top pod <pod-name>`",
                    "B) `kubectl logs <pod-name> --previous` followed by `kubectl describe pod <pod-name>`",
                    "C) `kubectl drain node`",
                    "D) `kubectl delete namespace`"
                ],
                correct_option=1,
                explanation="`kubectl logs --previous` fetches output from the crashed container, and `describe` reveals termination state (OOMKilled, ExitCode).",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="ops_mcq_2",
                type="mcq",
                modality="mcq_architecture",
                section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="VPC CIDR Subnetting & Usable IP Allocation",
                prompt="How many usable host IP addresses are available in an IPv4 subnet configured with a `/26` CIDR block in AWS/GCP VPC?",
                options=[
                    "A) 64 usable IPs",
                    "B) 59 usable IPs (64 total minus 5 network/router/DNS/broadcast reserved IPs)",
                    "C) 32 usable IPs",
                    "D) 256 usable IPs"
                ],
                correct_option=1,
                explanation="A /26 subnet has 2^(32-26) = 64 total addresses. Cloud providers reserve 5 IPs (network, VPC router, DNS, future, broadcast), leaving 59.",
                time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="ops_dsa_1",
                type="coding",
                modality="dsa_algorithms",
                section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Systems: Nginx Access Log Latency & Error Rate Parser",
                prompt="Parse raw Nginx log strings format `[status] [latency_ms]` and compute error count (status >= 500) and max latency.",
                starter_code={
                    "python": (
                        "def solution(logs):\n"
                        "    errors = 0\n"
                        "    max_lat = 0\n"
                        "    for line in logs:\n"
                        "        parts = line.strip().split()\n"
                        "        st = int(parts[0])\n"
                        "        lat = int(parts[1])\n"
                        "        if st >= 500:\n"
                        "            errors += 1\n"
                        "        if lat > max_lat:\n"
                        "            max_lat = lat\n"
                        "    return {'errors': errors, 'max_latency_ms': max_lat}\n"
                    )
                },
                test_cases=[{"input_data": [["200 45", "502 1200", "200 60", "500 80"]], "expected_output": {"errors": 2, "max_latency_ms": 1200}, "description": "Parse 4 log entries"}],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="ops_sql_1",
                type="sql",
                modality="sql_aggregation_analytics",
                section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Infrastructure Node Resource Utilization Aggregation",
                prompt="Write an SQL query to select node name and average CPU utilization for nodes with avg cpu >= 80%.",
                starter_code={
                    "sql": (
                        "SELECT node_name, ROUND(AVG(cpu_pct), 1) as avg_cpu\n"
                        "FROM node_metrics\n"
                        "GROUP BY node_name\n"
                        "HAVING AVG(cpu_pct) >= 80\n"
                        "ORDER BY avg_cpu DESC;\n"
                    )
                },
                test_cases=[{
                    "description": "Find high utilization nodes",
                    "setup_sql": "CREATE TABLE node_metrics (id INT, node_name TEXT, cpu_pct INT); INSERT INTO node_metrics VALUES (1, 'node-1', 85), (2, 'node-1', 95), (3, 'node-2', 40);",
                    "expected_output": [["node-1", 90.0]]
                }],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="ops_deb_1",
                type="debugging",
                modality="resilience_fault_tolerance",
                section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Exponential Backoff Delay Cap",
                prompt="Fix the exponential backoff calculation so delays cap at `max_delay_sec` without unbounded exponential growth.",
                starter_code={
                    "python": (
                        "def solution(attempts, base_delay_sec, max_delay_sec):\n"
                        "    delays = []\n"
                        "    for a in range(1, attempts + 1):\n"
                        "        d = min(max_delay_sec, base_delay_sec * (2 ** (a - 1)))\n"
                        "        delays.append(d)\n"
                        "    return delays\n"
                    )
                },
                test_cases=[{"input_data": [5, 1, 10], "expected_output": [1, 2, 4, 8, 10], "description": "5 attempts with base=1, max=10"}],
                time_limit_minutes=8
            )
        ]
    }
}


def _build_remaining_15_roles() -> Dict[str, Dict[str, Any]]:
    """Helper constructing the remaining 15 industry roles with 5 challenge types each."""
    tracks = {}

    # 6. FULLSTACK ENGINEER
    tracks["fullstack_engineer"] = {
        "track_id": "fullstack_engineer",
        "title": "Full Stack Engineer (API Architecture, DB & State)",
        "badge": "Full Stack & Auth",
        "description": "Evaluates JWT vs Session cookies, ORM N+1 queries, URL query canonicalization, and SQL user session auditing.",
        "skills": ["TypeScript", "Node.js", "Python", "React", "SQL", "REST", "GraphQL"],
        "questions": [
            AssessmentQuestion(
                id="fs_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="JWT vs Session Storage & XSS Defense",
                prompt="Which storage mechanism provides the strongest defense against unauthorized token exfiltration via Cross-Site Scripting (XSS)?",
                options=["A) `window.localStorage`", "B) `sessionStorage`", "C) `HttpOnly`, `Secure`, `SameSite=Strict` Cookie", "D) In-memory JavaScript object"],
                correct_option=2, explanation="HttpOnly cookies cannot be accessed by client-side JavaScript.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="fs_mcq_2", type="mcq", modality="mcq_architecture", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Database ORM N+1 Query Problem",
                prompt="In an ORM, what causes an 'N+1 query problem' when fetching 100 blog posts with their author names?",
                options=["A) Deadlock on concurrent locks.", "B) 1 query retrieves 100 posts, followed by 100 separate queries fetching each author.", "C) Pool exhaustion.", "D) Corrupted index."],
                correct_option=1, explanation="Sequentially executing 1 query for parents and N queries for child relations.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="fs_dsa_1", type="coding", modality="dsa_algorithms", section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Full Stack: Canonical URL Query Normalizer",
                prompt="Parse an unencoded query string, remove empty keys/values, sort keys alphabetically and format canonically.",
                starter_code={"python": "def solution(raw_query: str) -> str:\n    parts = raw_query.split('&')\n    valid = []\n    for p in parts:\n        if '=' in p:\n            k, v = p.split('=', 1)\n            if k and v: valid.append((k, v))\n    valid.sort(key=lambda x: (x[0], x[1]))\n    return '&'.join(f'{k}={v}' for k, v in valid)\n"},
                test_cases=[{"input_data": "b=2&a=apple&c=&a=apricot&d", "expected_output": "a=apple&a=apricot&b=2", "description": "Canonical sort"}],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="fs_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Active User Sessions per Tenant",
                prompt="Select tenant_id and count of active sessions where status = 'active' grouped by tenant_id.",
                starter_code={"sql": "SELECT tenant_id, COUNT(*) as active_count FROM user_sessions WHERE status = 'active' GROUP BY tenant_id ORDER BY active_count DESC;\n"},
                test_cases=[{
                    "description": "Count active sessions per tenant",
                    "setup_sql": "CREATE TABLE user_sessions (id INT, tenant_id TEXT, status TEXT); INSERT INTO user_sessions VALUES (1, 't1', 'active'), (2, 't1', 'active'), (3, 't2', 'expired');",
                    "expected_output": [["t1", 2]]
                }],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="fs_deb_1", type="debugging", modality="code_debugging", section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Memory Leak in Event Bus Listener Unsubscribe",
                prompt="Fix the event emitter unsubscribe function so removing non-existent or duplicate callbacks does not throw or corrupt state.",
                starter_code={"python": "class Bus:\n    def __init__(self): self.evs = {}\n    def on(self, e, cb): self.evs.setdefault(e, []).append(cb)\n    def off(self, e, cb):\n        if e in self.evs and cb in self.evs[e]: self.evs[e].remove(cb)\n    def emit(self, e, d): return [cb(d) for cb in self.evs.get(e, [])]\ndef solution(actions):\n    b = Bus(); res = []; f = {'h1': lambda d: f'1:{d}'}\n    for a, e, h in actions:\n        if a == 'on': b.on(e, f[h])\n        elif a == 'off': b.off(e, f[h])\n        elif a == 'emit': res.append(b.emit(e, h))\n    return res\n"},
                test_cases=[{"input_data": [[["on", "x", "h1"], ["emit", "x", "hi"], ["off", "x", "h1"], ["emit", "x", "bye"]]], "expected_output": [["1:hi"], []], "description": "Unsubscribe test"}],
                time_limit_minutes=8
            )
        ]
    }

    # 7. SECURITY ENGINEER
    tracks["security_engineer"] = {
        "track_id": "security_engineer",
        "title": "Cybersecurity & Application Security Engineer (AppSec)",
        "badge": "AppSec & Defense",
        "description": "Evaluates IDOR, CORS security misconfigurations, blind SQL injection, malicious payload sanitizers, and constant-time token comparison.",
        "skills": ["AppSec", "Penetration Testing", "OWASP Top 10", "Cryptography", "Python", "SQL"],
        "questions": [
            AssessmentQuestion(
                id="sec_mcq_1", type="mcq", modality="security_audit", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Insecure Direct Object References (IDOR)",
                prompt="What is the root cause of an Insecure Direct Object Reference (IDOR) vulnerability?",
                options=["A) Missing index.", "B) Server fails to enforce object-level authorization checking whether the caller owns the resource.", "C) Use of HTTP GET.", "D) Plaintext HTTP."],
                correct_option=1, explanation="Missing object-level access control on parameter IDs.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="sec_mcq_2", type="mcq", modality="security_audit", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="CORS: Wildcard Origin with Credentials",
                prompt="Why do modern browsers reject HTTP responses with Access-Control-Allow-Origin: * when Access-Control-Allow-Credentials: true is set?",
                options=["A) TLS 1.3 requirement.", "B) It would allow arbitrary websites to exfiltrate private authenticated data using session cookies.", "C) High CPU cost.", "D) HTTP/2 syntax violation."],
                correct_option=1, explanation="Violates origin isolation and browser credential safety.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="sec_dsa_1", type="coding", modality="security_audit", section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Security: SQL Injection & XSS Signature Detector",
                prompt="Analyze payload for SQLi (' or '1'='1, --, union select) or XSS (<script>, javascript:, onerror=) and return safety dict.",
                starter_code={"python": "def solution(payload: str):\n    p = payload.lower()\n    threats = []\n    if any(s in p for s in [\"' or '1'='1\", \"--\", \"union select\", \"; drop\"]): threats.append('sqli')\n    if any(s in p for s in [\"<script>\", \"javascript:\", \"onerror=\"]): threats.append('xss')\n    return {'is_safe': len(threats) == 0, 'threats': sorted(threats)}\n"},
                test_cases=[{"input_data": "admin' OR '1'='1' --", "expected_output": {"is_safe": False, "threats": ["sqli"]}, "description": "Detect SQLi"}],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="sec_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Audit High-Risk Failed Login Attempts",
                prompt="Query audit_logs to count failed logins per IP address where failure count >= 3.",
                starter_code={"sql": "SELECT ip_address, COUNT(*) as failed_count FROM audit_logs WHERE action = 'login_failed' GROUP BY ip_address HAVING COUNT(*) >= 3 ORDER BY failed_count DESC;\n"},
                test_cases=[{
                    "description": "Find IPs with >= 3 failed logins",
                    "setup_sql": "CREATE TABLE audit_logs (id INT, ip_address TEXT, action TEXT); INSERT INTO audit_logs VALUES (1, '10.0.0.1', 'login_failed'), (2, '10.0.0.1', 'login_failed'), (3, '10.0.0.1', 'login_failed'), (4, '10.0.0.2', 'login_failed');",
                    "expected_output": [["10.0.0.1", 3]]
                }],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="sec_deb_1", type="debugging", modality="code_debugging", section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Constant-Time Signature Comparison",
                prompt="Fix string token comparison to use constant-time `hmac.compare_digest` to eliminate timing side-channel attacks.",
                starter_code={"python": "import hmac\ndef solution(token_a: str, token_b: str) -> bool:\n    if not isinstance(token_a, str) or not isinstance(token_b, str): return False\n    return hmac.compare_digest(token_a, token_b)\n"},
                test_cases=[{"input_data": ["sec_123", "sec_123"], "expected_output": True, "description": "Constant time equality"}],
                time_limit_minutes=8
            )
        ]
    }

    # 8. DATA ANALYST
    tracks["data_analyst"] = {
        "track_id": "data_analyst",
        "title": "Data Analyst & Business Intelligence (SQL Analytics & BI)",
        "badge": "SQL Analytics & BI",
        "description": "Evaluates customer churn, dimensional modeling, Month-over-Month revenue growth calculation with LAG(), and customer lifetime spend tiers.",
        "skills": ["SQL", "Data Analytics", "Tableau/PowerBI", "Python", "Statistics", "Metrics"],
        "questions": [
            AssessmentQuestion(
                id="da_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Customer Churn Rate Calculation Standard",
                prompt="What is the industry-standard formula for calculating Customer Churn Rate for a given calendar month?",
                options=["A) New Customers / Total at End * 100", "B) (Customers Lost during Month) / (Total at Start of Month) * 100", "C) MRR / CAC", "D) Inactive / Views"],
                correct_option=1, explanation="Lost customers divided by starting customer baseline.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="da_mcq_2", type="mcq", modality="mcq_architecture", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Type 2 Slowly Changing Dimension (SCD Type 2)",
                prompt="In a dimensional data warehouse, how does an SCD Type 2 handle customer address changes?",
                options=["A) Overwrite old address.", "B) Duplicate table annually.", "C) Insert new record with valid date ranges (start_date, end_date), preserving historical audit trail.", "D) Delete old transactions."],
                correct_option=2, explanation="Preserves full historical truth with start/end effective timestamps.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="da_dsa_1", type="coding", modality="dsa_algorithms", section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Analytics: Customer Cohort Retention Rate Matrix",
                prompt="Given user signups and activity months, return percentage of users active in month 1 and month 2.",
                starter_code={"python": "def solution(cohort_size, m1_active, m2_active):\n    ret_m1 = round((m1_active / cohort_size) * 100.0, 1)\n    ret_m2 = round((m2_active / cohort_size) * 100.0, 1)\n    return {'m1_pct': ret_m1, 'm2_pct': ret_m2}\n"},
                test_cases=[{"input_data": [1000, 600, 450], "expected_output": {"m1_pct": 60.0, "m2_pct": 45.0}, "description": "Calculate retention rates"}],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="da_sql_1", type="sql", modality="sql_window_cte", section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Month-over-Month (MoM) Revenue Growth % with LAG()",
                prompt="Write an SQL query to calculate Month-over-Month (MoM) revenue growth percentage using `LAG(revenue) OVER (ORDER BY month)`.",
                starter_code={"sql": "WITH rev_lag AS (\n    SELECT month, revenue, LAG(revenue) OVER (ORDER BY month) as prev_rev\n    FROM monthly_sales\n)\nSELECT month, revenue,\n       CASE WHEN prev_rev IS NULL THEN NULL\n            ELSE ROUND(((revenue - prev_rev) * 100.0) / prev_rev, 1) END as mom_growth_pct\nFROM rev_lag\nORDER BY month ASC;\n"},
                test_cases=[{
                    "description": "Calculate MoM changes across 3 months",
                    "setup_sql": "CREATE TABLE monthly_sales (month TEXT, revenue INT); INSERT INTO monthly_sales VALUES ('2026-01', 10000), ('2026-02', 15000), ('2026-03', 12000);",
                    "expected_output": [["2026-01", 10000, None], ["2026-02", 15000, 50.0], ["2026-03", 12000, -20.0]]
                }],
                time_limit_minutes=10
            ),
            AssessmentQuestion(
                id="da_deb_1", type="debugging", modality="code_debugging", section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix ZeroDivisionError in Conversion Rate Calculator",
                prompt="Fix the conversion rate calculation so it safely handles zero-impression edge cases without raising ZeroDivisionError.",
                starter_code={"python": "def solution(clicks, impressions):\n    if not impressions or impressions <= 0: return 0.0\n    return round((clicks / impressions) * 100.0, 2)\n"},
                test_cases=[{"input_data": [50, 0], "expected_output": 0.0, "description": "Safe zero impression handling"}],
                time_limit_minutes=8
            )
        ]
    }

    # 9. QA AUTOMATION ENGINEER
    tracks["qa_automation_engineer"] = {
        "track_id": "qa_automation_engineer",
        "title": "SDET & QA Automation Engineer (Test Harnesses & Quality)",
        "badge": "Automation & SDET",
        "description": "Evaluates flaky test mitigation, testing pyramid, retry runners, and JSON response schema validation.",
        "skills": ["Python", "Selenium", "Playwright", "PyTest", "CI/CD", "API Testing", "SQL"],
        "questions": [
            AssessmentQuestion(
                id="qa_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Flaky Test Root Causes & Mitigation",
                prompt="Which factor is the most common root cause of 'flaky' test failures in modern E2E automation suites?",
                options=["A) TypeScript 5.", "B) Asynchronous timing races, hardcoded sleeps, and shared unmanaged test state.", "C) Running on Linux.", "D) CSS selectors."],
                correct_option=1, explanation="Race conditions and state pollution cause non-deterministic failures.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="qa_mcq_2", type="mcq", modality="mcq_architecture", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Testing Pyramid Architecture",
                prompt="According to the Martin Fowler Testing Pyramid, what should comprise the largest volume of tests?",
                options=["A) E2E UI tests.", "B) Manual smoke tests.", "C) Fast, isolated Unit Tests.", "D) Visual screenshots."],
                correct_option=2, explanation="Unit tests provide the fastest feedback with lowest maintenance overhead.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="qa_dsa_1", type="coding", modality="resilience_fault_tolerance", section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="QA Automation: Flaky Operation Retry Runner Simulation",
                prompt="Simulate retrying a network operation up to max_retries attempts until True is returned.",
                starter_code={"python": "def solution(attempt_statuses, max_retries):\n    attempts = 0\n    for s in attempt_statuses[:max_retries]:\n        attempts += 1\n        if s: return {'succeeded': True, 'attempts_made': attempts}\n    return {'succeeded': False, 'attempts_made': attempts}\n"},
                test_cases=[{"input_data": [[False, False, True], 3], "expected_output": {"succeeded": True, "attempts_made": 3}, "description": "Succeed on attempt 3"}],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="qa_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Flaky Test Run Failure Rate Benchmark",
                prompt="Calculate pass rate % (`passed_count * 100.0 / total_runs`) per test suite from `test_runs`.",
                starter_code={"sql": "SELECT suite_name, ROUND((SUM(passed) * 100.0) / COUNT(*), 1) as pass_rate\nFROM test_runs\nGROUP BY suite_name\nORDER BY pass_rate ASC;\n"},
                test_cases=[{
                    "description": "Calculate pass rate",
                    "setup_sql": "CREATE TABLE test_runs (id INT, suite_name TEXT, passed INT); INSERT INTO test_runs VALUES (1, 'auth', 1), (2, 'auth', 1), (3, 'checkout', 0), (4, 'checkout', 1);",
                    "expected_output": [["checkout", 50.0], ["auth", 100.0]]
                }],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="qa_deb_1", type="debugging", modality="data_transformation", section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix JSON Response Schema Validator",
                prompt="Fix the nested dot-notation key lookup in the JSON schema validator.",
                starter_code={"python": "def solution(data, required_keys):\n    for key in required_keys:\n        curr = data\n        for p in key.split('.'):\n            if not isinstance(curr, dict) or p not in curr: return False\n            curr = curr[p]\n    return True\n"},
                test_cases=[{"input_data": [{"user": {"id": 1, "profile": {"email": "a@b.com"}}}, ["user.id", "user.profile.email"]], "expected_output": True, "description": "Validate nested keys"}],
                time_limit_minutes=8
            )
        ]
    }

    # 10. MOBILE ENGINEER
    tracks["mobile_engineer"] = {
        "track_id": "mobile_engineer",
        "title": "Mobile Engineer (iOS, Android & Cross-Platform)",
        "badge": "Mobile & Offline-First",
        "description": "Evaluates mobile lifecycle eviction, SQLite local cache sync, push notification protocols, LRU memory caches, and memory leak prevention.",
        "skills": ["Swift", "Kotlin", "React Native", "Flutter", "SQLite", "Mobile Architecture"],
        "questions": [
            AssessmentQuestion(
                id="mob_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Mobile Lifecycle & Background Eviction",
                prompt="What occurs when a mobile OS encounters memory pressure while an application is backgrounded?",
                options=["A) Restarts phone.", "B) Forcefully terminates background process without guaranteed termination hooks.", "C) Swaps to SD card.", "D) System pop-up."],
                correct_option=1, explanation="OS terminates background processes without warning to reclaim memory.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="mob_mcq_2", type="mcq", modality="mcq_architecture", section="mcq",
                section_title="Section 1: Multiple Choice Questions (MCQs)",
                title="Offline-First Mobile Synchronization",
                prompt="In offline-first mobile apps, how should user writes be handled without active internet?",
                options=["A) Block UI spinner.", "B) Discard user input.", "C) Write immediately to local embedded database and queue for background sync upon reconnect.", "D) Send via SMS."],
                correct_option=2, explanation="Local optimistic write ensures responsive UX with offline durability.", time_limit_minutes=2
            ),
            AssessmentQuestion(
                id="mob_dsa_1", type="coding", modality="performance_optimization", section="coding",
                section_title="Section 2: Coding & DSA Challenges",
                title="Mobile Systems: In-Memory LRU Cache for Image Thumbnails",
                prompt="Implement an LRU cache simulation supporting `put(k, v)` and `get(k)` with fixed capacity.",
                starter_code={"python": "from collections import OrderedDict\ndef solution(capacity, operations):\n    cache = OrderedDict(); res = []\n    for op in operations:\n        if op[0] == 'put':\n            k, v = op[1], op[2]\n            if k in cache: cache.move_to_end(k)\n            cache[k] = v\n            if len(cache) > capacity: cache.popitem(last=False)\n        elif op[0] == 'get':\n            k = op[1]\n            if k in cache:\n                cache.move_to_end(k); res.append(cache[k])\n            else: res.append(-1)\n    return res\n"},
                test_cases=[{"input_data": [2, [["put", 1, "a"], ["put", 2, "b"], ["get", 1], ["put", 3, "c"], ["get", 2]]], "expected_output": ["a", -1], "description": "LRU evicts key 2"}],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="mob_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql",
                section_title="Section 2: Interactive SQL & Data Challenges",
                title="SQL: Offline Sync Mutation Queue Processing",
                prompt="Select sync mutations that have status = 'pending' ordered by created_at ASC.",
                starter_code={"sql": "SELECT entity_type, entity_id, payload FROM sync_queue WHERE status = 'pending' ORDER BY created_at ASC;\n"},
                test_cases=[{
                    "description": "Fetch pending mutations",
                    "setup_sql": "CREATE TABLE sync_queue (id INT, entity_type TEXT, entity_id TEXT, payload TEXT, status TEXT, created_at INT); INSERT INTO sync_queue VALUES (1, 'contact', 'c1', '{\"name\":\"A\"}', 'pending', 100), (2, 'contact', 'c2', '{\"name\":\"B\"}', 'synced', 105);",
                    "expected_output": [["contact", "c1", '{"name":"A"}']]
                }],
                time_limit_minutes=8
            ),
            AssessmentQuestion(
                id="mob_deb_1", type="debugging", modality="code_debugging", section="coding",
                section_title="Section 2: Code Debugging & Threat Defense",
                title="Debugging: Fix Retain Cycle in Notification Observer Unregister",
                prompt="Fix observer unregister logic so callbacks remove cleanly upon view teardown.",
                starter_code={"python": "def solution(events):\n    obs = {}; dispatched = []\n    for act in events:\n        if act[0] == 'sub': obs.setdefault(act[2], set()).add(act[1])\n        elif act[0] == 'unsub':\n            for s in obs.values(): s.discard(act[1])\n        elif act[0] == 'notify': dispatched.append(sorted(list(obs.get(act[1], set()))))\n    return dispatched\n"},
                test_cases=[{"input_data": [[["sub", "v1", "push"], ["sub", "v2", "push"], ["unsub", "v1"], ["notify", "push"]]], "expected_output": [["v2"]], "description": "Unregister v1"}],
                time_limit_minutes=8
            )
        ]
    }

    # 11. CLOUD ARCHITECT
    tracks["cloud_architect"] = {
        "track_id": "cloud_architect", "title": "Cloud Solutions Architect (Distributed & Multi-Region)",
        "badge": "Cloud Architecture", "description": "Multi-region failover, egress cost optimization, CAP theorem, and distributed locking.",
        "skills": ["AWS", "GCP", "Terraform", "Distributed Systems", "Cost Optimization", "SQL"],
        "questions": [
            AssessmentQuestion(id="ca_mcq_1", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="CAP Theorem in Global Replicated Databases", prompt="Under network partition (P), what must a globally distributed database choose between?", options=["A) Speed vs Encryption", "B) Consistency vs Availability", "C) Throughput vs Storage", "D) CPU vs Memory"], correct_option=1, explanation="Brewer's CAP theorem states a partition forces trade-off between C and A.", time_limit_minutes=2),
            AssessmentQuestion(id="ca_mcq_2", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Cloud Egress Cost Mitigation", prompt="What is the most cost-effective method to transfer petabytes between services in the same cloud region?", options=["A) Public internet IP routing", "B) VPC Endpoints / PrivateLink", "C) VPN Gateway", "D) NAT Gateway"], correct_option=1, explanation="VPC peering/endpoints avoid internet data egress tolls.", time_limit_minutes=2),
            AssessmentQuestion(id="ca_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Cloud Architecture: Multi-Region Latency Route Optimizer", prompt="Given a client location and list of region endpoints with latencies, return closest region name.", starter_code={"python": "def solution(client_ip, region_latencies):\n    return min(region_latencies, key=lambda x: x[1])[0]\n"}, test_cases=[{"input_data": ["1.2.3.4", [["us-east", 45], ["eu-west", 110], ["us-west", 15]]], "expected_output": "us-west", "description": "Select min latency region"}], time_limit_minutes=8),
            AssessmentQuestion(id="ca_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: Monthly Cloud Service Cost Anomaly Detector", prompt="Find cloud services where total monthly cost exceeded $5000.", starter_code={"sql": "SELECT service_name, SUM(cost) as total_cost FROM cloud_billing GROUP BY service_name HAVING SUM(cost) > 5000 ORDER BY total_cost DESC;\n"}, test_cases=[{"description": "High cost services", "setup_sql": "CREATE TABLE cloud_billing (id INT, service_name TEXT, cost INT); INSERT INTO cloud_billing VALUES (1, 'EC2', 3500), (2, 'EC2', 2500), (3, 'S3', 400);", "expected_output": [["EC2", 6000]]}], time_limit_minutes=8),
            AssessmentQuestion(id="ca_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Distributed Lease Expiration Race", prompt="Fix lease check so expired leases can be claimed by new candidates.", starter_code={"python": "def solution(lease_owner, lease_expire_ts, current_ts, candidate):\n    if current_ts >= lease_expire_ts:\n        return {'owner': candidate, 'status': 'acquired'}\n    return {'owner': lease_owner, 'status': 'locked'}\n"}, test_cases=[{"input_data": ["node1", 100, 105, "node2"], "expected_output": {"owner": "node2", "status": "acquired"}, "description": "Acquire expired lease"}], time_limit_minutes=8)
        ]
    }

    # 12. DATABASE ADMINISTRATOR (DBA)
    tracks["database_administrator"] = {
        "track_id": "database_administrator", "title": "Database Administrator & Performance Engineer (DBA)",
        "badge": "DBA & Performance", "description": "B-Tree vs LSM trees, WAL journaling, connection pooling, slow query analysis, and index bloat.",
        "skills": ["PostgreSQL", "MySQL", "Query Optimization", "Indexing", "WAL", "Replication", "SQL"],
        "questions": [
            AssessmentQuestion(id="dba_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="B-Tree vs LSM-Tree Write Amplification", prompt="Why do Log-Structured Merge (LSM) trees achieve higher sequential write throughput than B-Trees?", options=["A) LSM trees skip disk storage completely.", "B) LSM trees append writes sequentially to a memtable and WAL before flushing to SSTables.", "C) LSM trees require no indexing.", "D) LSM trees only run on NVMe."], correct_option=1, explanation="LSM turns random disk writes into batched sequential I/O.", time_limit_minutes=2),
            AssessmentQuestion(id="dba_mcq_2", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="PostgreSQL Vacuuming & Bloat", prompt="What is the purpose of VACUUM in PostgreSQL's MVCC architecture?", options=["A) Deletes database backups.", "B) Reclaims storage occupied by dead row versions (tuples) from updates and deletes.", "C) Upgrades database schema.", "D) Shuts down inactive connections."], correct_option=1, explanation="MVCC updates create new tuples; VACUUM reclaims dead tuple disk space.", time_limit_minutes=2),
            AssessmentQuestion(id="dba_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="DBA: Connection Pool Queue Fairness Simulator", prompt="Simulate FIFO connection pool checkout where requests borrow connections up to max_pool_size.", starter_code={"python": "def solution(requests, max_pool):\n    granted = []\n    for req in requests:\n        granted.append(len(granted) < max_pool)\n    return granted\n"}, test_cases=[{"input_data": [["r1", "r2", "r3"], 2], "expected_output": [True, True, False], "description": "Pool cap 2"}], time_limit_minutes=8),
            AssessmentQuestion(id="dba_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: Slow Query Execution Log Analysis", prompt="Select query template and average duration for queries where avg duration > 200ms.", starter_code={"sql": "SELECT query_template, ROUND(AVG(duration_ms), 1) as avg_duration FROM query_logs GROUP BY query_template HAVING AVG(duration_ms) > 200 ORDER BY avg_duration DESC;\n"}, test_cases=[{"description": "Find slow queries", "setup_sql": "CREATE TABLE query_logs (id INT, query_template TEXT, duration_ms INT); INSERT INTO query_logs VALUES (1, 'SELECT * FROM users', 300), (2, 'SELECT * FROM users', 250), (3, 'SELECT 1', 2);", "expected_output": [["SELECT * FROM users", 275.0]]}], time_limit_minutes=8),
            AssessmentQuestion(id="dba_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Deadlock Circular Dependency Detector", prompt="Fix cycle detection in wait-for graph so it correctly flags circular deadlocks.", starter_code={"python": "def solution(graph):\n    visited = set(); rec = set()\n    def has_cycle(n):\n        visited.add(n); rec.add(n)\n        for nei in graph.get(n, []):\n            if nei not in visited:\n                if has_cycle(nei): return True\n            elif nei in rec: return True\n        rec.remove(n)\n        return False\n    for node in graph:\n        if node not in visited:\n            if has_cycle(node): return True\n    return False\n"}, test_cases=[{"input_data": [{"t1": ["t2"], "t2": ["t1"]}], "expected_output": True, "description": "Detect 2-tx deadlock cycle"}], time_limit_minutes=8)
        ]
    }

    # 13. BLOCKCHAIN & WEB3 ENGINEER
    tracks["blockchain_engineer"] = {
        "track_id": "blockchain_engineer", "title": "Web3 & Blockchain Engineer (Smart Contracts & Crypto)",
        "badge": "Web3 & Cryptography", "description": "EVM gas mechanics, reentrancy attacks, Merkle tree verification, transaction logs, and cryptographic hashing.",
        "skills": ["Solidity", "EVM", "Cryptography", "Python", "Rust", "Web3", "SQL"],
        "questions": [
            AssessmentQuestion(id="bc_mcq_1", type="mcq", modality="security_audit", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Smart Contract Reentrancy Vulnerability", prompt="What programming pattern permanently protects Solidity contracts against reentrancy exploits?", options=["A) Using tx.origin.", "B) Checks-Effects-Interactions pattern and nonReentrant reentrancy mutex guard.", "C) Calling selfdestruct.", "D) Increasing block gas limit."], correct_option=1, explanation="Modifying state before external contract calls prevents recursive reentrancy.", time_limit_minutes=2),
            AssessmentQuestion(id="bc_mcq_2", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Proof of Stake Finality", prompt="What does 'finality' mean in blockchain consensus protocols?", options=["A) The wallet balance reaches zero.", "B) A block is permanently committed and cannot be altered or reverted without severe slashing.", "C) Gas price reaches maximum.", "D) The node goes offline."], correct_option=1, explanation="Finality guarantees that transactions cannot be reorganized or forged.", time_limit_minutes=2),
            AssessmentQuestion(id="bc_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Web3: Merkle Root Hash Pair Builder", prompt="Given two hex leaf hashes, compute their sorted concatenation sha256 digest hex.", starter_code={"python": "import hashlib\ndef solution(leaf_a, leaf_b):\n    pair = sorted([leaf_a, leaf_b])\n    return hashlib.sha256((pair[0] + pair[1]).encode('utf-8')).hexdigest()\n"}, test_cases=[{"input_data": ["abc", "123"], "expected_output": "64ec88ca02bc14a0fec50e4d41cb71cbde02fc07c8a27ff3297507971b07d4f1", "description": "Deterministic sorted pair hash"}], time_limit_minutes=8),
            AssessmentQuestion(id="bc_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: Whale Wallet Transaction Volume Tracker", prompt="Select wallet address and sum of eth_value for wallets with total volume > 50 ETH.", starter_code={"sql": "SELECT wallet_address, SUM(eth_value) as total_vol FROM eth_transactions GROUP BY wallet_address HAVING SUM(eth_value) > 50 ORDER BY total_vol DESC;\n"}, test_cases=[{"description": "Whale volume query", "setup_sql": "CREATE TABLE eth_transactions (id INT, wallet_address TEXT, eth_value INT); INSERT INTO eth_transactions VALUES (1, '0x1', 40), (2, '0x1', 25), (3, '0x2', 5);", "expected_output": [["0x1", 65]]}], time_limit_minutes=8),
            AssessmentQuestion(id="bc_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix EVM Gas Counter Calculation Underflow", prompt="Fix gas calculation to prevent integer underflow when consumed gas exceeds gas limit.", starter_code={"python": "def solution(gas_limit, gas_used):\n    if gas_used > gas_limit: return 0\n    return gas_limit - gas_used\n"}, test_cases=[{"input_data": [1000, 1200], "expected_output": 0, "description": "Prevent negative gas underflow"}], time_limit_minutes=8)
        ]
    }

    # 14. EMBEDDED & IOT FIRMWARE ENGINEER
    tracks["embedded_iot_engineer"] = {
        "track_id": "embedded_iot_engineer", "title": "Embedded Systems & IoT Firmware Engineer",
        "badge": "Firmware & Bitwise", "description": "Interrupt Service Routines (ISRs), UART/SPI/I2C protocols, bitwise register masks, and sensor telemetry.",
        "skills": ["C/C++", "Bitwise", "RTOS", "I2C/SPI", "Python", "Hardware", "SQL"],
        "questions": [
            AssessmentQuestion(id="iot_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Interrupt Service Routine (ISR) Rules", prompt="Why must blocking operations like `sleep` or heavy memory allocation `malloc` never be called inside an ISR?", options=["A) ISRs lack compiler support.", "B) ISRs run with interrupts masked; blocking delays the CPU and misses critical hardware timing deadlines.", "C) ISRs only run on GPU cores.", "D) It triggers an immediate reboot."], correct_option=1, explanation="ISRs must execute and return with sub-microsecond latency.", time_limit_minutes=2),
            AssessmentQuestion(id="iot_mcq_2", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="I2C vs SPI Bus Protocol Trade-Off", prompt="What is the primary advantage of SPI over I2C for high-speed sensor streams?", options=["A) SPI uses only 2 wires.", "B) SPI supports full-duplex transmission with dedicated chip-selects and significantly higher clock rates (tens of MHz).", "C) SPI supports multi-master arbitration on 1 wire.", "D) SPI requires no power."], correct_option=1, explanation="SPI achieves much higher data rates using dedicated MISO/MOSI channels.", time_limit_minutes=2),
            AssessmentQuestion(id="iot_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Embedded: Bitwise Hardware Register Mask & Toggle", prompt="Given a 16-bit register value, apply bitwise operations to set bit N, clear bit M, and return updated integer.", starter_code={"python": "def solution(reg, set_bit, clear_bit):\n    reg = reg | (1 << set_bit)\n    reg = reg & ~(1 << clear_bit)\n    return reg\n"}, test_cases=[{"input_data": [0, 2, 4], "expected_output": 4, "description": "Set bit 2 (value 4)"}], time_limit_minutes=8),
            AssessmentQuestion(id="iot_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: IoT Device Overheating Telemetry Alerts", prompt="Select device_id and max temperature where max temperature exceeds 85 degrees.", starter_code={"sql": "SELECT device_id, MAX(temp_c) as max_temp FROM sensor_data GROUP BY device_id HAVING MAX(temp_c) > 85 ORDER BY max_temp DESC;\n"}, test_cases=[{"description": "High temp devices", "setup_sql": "CREATE TABLE sensor_data (id INT, device_id TEXT, temp_c INT); INSERT INTO sensor_data VALUES (1, 'sensor-a', 90), (2, 'sensor-a', 82), (3, 'sensor-b', 70);", "expected_output": [["sensor-a", 90]]}], time_limit_minutes=8),
            AssessmentQuestion(id="iot_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Ring Buffer Circular Pointer Wrap", prompt="Fix circular buffer write pointer wrap so index wraps modulo capacity.", starter_code={"python": "def solution(capacity, items):\n    buf = [None] * capacity\n    idx = 0\n    for it in items:\n        buf[idx % capacity] = it\n        idx += 1\n    return buf\n"}, test_cases=[{"input_data": [3, [1, 2, 3, 4]], "expected_output": [4, 2, 3], "description": "Overwriting index 0 with item 4"}], time_limit_minutes=8)
        ]
    }

    # 15. NLP & LLM ENGINEER
    tracks["nlp_engineer"] = {
        "track_id": "nlp_engineer", "title": "NLP & Large Language Model Engineer (LLMs & RAG)",
        "badge": "LLMs & GenAI", "description": "BPE tokenization, RAG chunking, vector indexing, hallucination benchmarks, and prompt routing.",
        "skills": ["LLMs", "RAG", "Embeddings", "Transformers", "Python", "Vector DB", "SQL"],
        "questions": [
            AssessmentQuestion(id="nlp_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Byte Pair Encoding (BPE) Subword Tokenization", prompt="Why do modern LLMs (GPT-4, Gemini) use subword tokenizers like BPE instead of word-level tokenization?", options=["A) Word-level tokenizers require GPUs.", "B) Subword tokenization handles unseen out-of-vocabulary words by breaking them into frequent subword units while keeping vocabulary size manageable.", "C) Words cannot be embedded into vectors.", "D) BPE guarantees zero prompt cost."], correct_option=1, explanation="Subword BPE prevents Out-Of-Vocabulary exceptions while compressing vocabulary.", time_limit_minutes=2),
            AssessmentQuestion(id="nlp_mcq_2", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Retrieval Augmented Generation (RAG) Chunking", prompt="What is the consequence of choosing an excessively large chunk size (e.g. 4000 tokens) in a vector RAG pipeline?", options=["A) The vector database crashes.", "B) Retrieved chunks contain too much diluted irrelevant noise, degrading model precision and increasing hallucination.", "C) Embedding vectors become 1-dimensional.", "D) It violates cosine similarity laws."], correct_option=1, explanation="Overly large chunks drown relevant facts in context noise.", time_limit_minutes=2),
            AssessmentQuestion(id="nlp_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="NLP: Text Chunking with Overlapping Sliding Window", prompt="Chunk text tokens into slices of size `chunk_size` with `overlap` tokens shared between consecutive chunks.", starter_code={"python": "def solution(tokens, chunk_size, overlap):\n    step = chunk_size - overlap\n    chunks = []\n    for i in range(0, len(tokens), step):\n        c = tokens[i:i + chunk_size]\n        chunks.append(c)\n        if i + chunk_size >= len(tokens): break\n    return chunks\n"}, test_cases=[{"input_data": [["a", "b", "c", "d", "e"], 3, 1], "expected_output": [["a", "b", "c"], ["c", "d", "e"]], "description": "Overlapping chunks"}], time_limit_minutes=8),
            AssessmentQuestion(id="nlp_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: LLM Token Usage & Cost by Prompt Template", prompt="Calculate total prompt tokens and completion tokens grouped by template_id.", starter_code={"sql": "SELECT template_id, SUM(prompt_tokens) as total_prompt, SUM(completion_tokens) as total_comp FROM llm_logs GROUP BY template_id ORDER BY total_prompt DESC;\n"}, test_cases=[{"description": "Aggregate LLM tokens", "setup_sql": "CREATE TABLE llm_logs (id INT, template_id TEXT, prompt_tokens INT, completion_tokens INT); INSERT INTO llm_logs VALUES (1, 't_rag', 500, 100), (2, 't_rag', 400, 80), (3, 't_chat', 150, 50);", "expected_output": [["t_rag", 900, 180], ["t_chat", 150, 50]]}], time_limit_minutes=8),
            AssessmentQuestion(id="nlp_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Cosine Distance Inversion Bug", prompt="Fix cosine distance formula `distance = 1.0 - similarity` so smaller distance represents closer vectors.", starter_code={"python": "def solution(similarity):\n    return round(1.0 - similarity, 4)\n"}, test_cases=[{"input_data": 0.85, "expected_output": 0.15, "description": "Cosine distance is 1 - sim"}], time_limit_minutes=8)
        ]
    }

    # 16. COMPUTER VISION ENGINEER
    tracks["computer_vision_engineer"] = {
        "track_id": "computer_vision_engineer", "title": "Computer Vision Engineer (CNNs & Object Detection)",
        "badge": "Vision & Convolutions", "description": "Convolutions, Intersection over Union (IoU), Non-Maximum Suppression (NMS), and inference benchmarks.",
        "skills": ["OpenCV", "PyTorch", "CNNs", "Object Detection", "Python", "SQL"],
        "questions": [
            AssessmentQuestion(id="cv_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Convolutional Layer Invariance", prompt="What spatial property do Convolutional Neural Networks (CNNs) inherently possess due to weight sharing?", options=["A) Rotation invariance", "B) Translation equivariance (detecting features regardless of position in image)", "C) Infinite depth invariance", "D) Scale independence"], correct_option=1, explanation="Convolution kernels detect identical patterns across spatial coordinates.", time_limit_minutes=2),
            AssessmentQuestion(id="cv_mcq_2", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Non-Maximum Suppression (NMS) in Object Detection", prompt="What is the objective of Non-Maximum Suppression (NMS) in object detection algorithms (YOLO, Faster R-CNN)?", options=["A) To convert images to grayscale.", "B) To eliminate redundant overlapping bounding boxes predicting the same object based on IoU threshold.", "C) To resize input images.", "D) To increase camera shutter speed."], correct_option=1, explanation="NMS prunes overlapping candidate boxes, keeping the highest confidence box.", time_limit_minutes=2),
            AssessmentQuestion(id="cv_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Vision DSA: Intersection over Union (IoU) Calculator", prompt="Calculate IoU between two 1D bounding box intervals `[start, end]`. Return rounded float to 2 decimal places.", starter_code={"python": "def solution(box1, box2):\n    inter_start = max(box1[0], box2[0])\n    inter_end = min(box1[1], box2[1])\n    inter = max(0, inter_end - inter_start)\n    union = (box1[1] - box1[0]) + (box2[1] - box2[0]) - inter\n    if union <= 0: return 0.0\n    return round(inter / union, 2)\n"}, test_cases=[{"input_data": [[0, 10], [5, 15]], "expected_output": 0.33, "description": "5 overlap over 15 union"}], time_limit_minutes=8),
            AssessmentQuestion(id="cv_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: Object Detection Class Count Breakdown", prompt="Count detected objects grouped by class_label where confidence >= 0.8.", starter_code={"sql": "SELECT class_label, COUNT(*) as count FROM detections WHERE confidence >= 0.8 GROUP BY class_label ORDER BY count DESC;\n"}, test_cases=[{"description": "High confidence detections", "setup_sql": "CREATE TABLE detections (id INT, class_label TEXT, confidence REAL); INSERT INTO detections VALUES (1, 'car', 0.95), (2, 'car', 0.85), (3, 'pedestrian', 0.50);", "expected_output": [["car", 2]]}], time_limit_minutes=8),
            AssessmentQuestion(id="cv_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Bounding Box Coordinate Normalization", prompt="Normalize bounding box coordinates `[x, y, w, h]` into `[0, 1]` floats relative to image width and height.", starter_code={"python": "def solution(box, img_w, img_h):\n    return [round(box[0] / img_w, 2), round(box[1] / img_h, 2), round(box[2] / img_w, 2), round(box[3] / img_h, 2)]\n"}, test_cases=[{"input_data": [[100, 200, 50, 80], 1000, 1000], "expected_output": [0.1, 0.2, 0.05, 0.08], "description": "Normalized coordinates"}], time_limit_minutes=8)
        ]
    }

    # 17. PLATFORM ENGINEER
    tracks["platform_engineer"] = {
        "track_id": "platform_engineer", "title": "Platform & Developer Experience Engineer",
        "badge": "Internal Developer Platforms", "description": "Internal developer platforms, GitOps, Kubernetes CRDs, build pipeline SLAs, and developer productivity.",
        "skills": ["Kubernetes", "Helm", "Terraform", "GitOps", "ArgoCD", "Python", "SQL"],
        "questions": [
            AssessmentQuestion(id="plt_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="GitOps Principle of Desired State", prompt="What is the foundational principle of GitOps (e.g. ArgoCD, Flux)?", options=["A) Developers write code directly in production terminal.", "B) Git repository serves as the single source of truth; agents continuously reconcile cluster state to match Git.", "C) All deployments require manual GUI clicks.", "D) Discarding container registries."], correct_option=1, explanation="Continuous automated reconciliation between Git and runtime infrastructure.", time_limit_minutes=2),
            AssessmentQuestion(id="plt_mcq_2", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Kubernetes Custom Resource Definitions (CRDs)", prompt="What is a Custom Resource Definition (CRD) and Operator in Kubernetes?", options=["A) A CSS stylesheet for the Kubernetes dashboard.", "B) Extending the Kubernetes API with custom domain objects managed by an active control reconciliation loop.", "C) Replacing Docker with VirtualBox.", "D) Deleting etcd keys."], correct_option=1, explanation="CRDs extend the Kubernetes API and Operators automate custom operational lifecycle.", time_limit_minutes=2),
            AssessmentQuestion(id="plt_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Platform: Semantic Version Dependency Conflict Resolver", prompt="Compare two semver strings `v1` and `v2`. Return 1 if v1 > v2, -1 if v1 < v2, 0 if equal.", starter_code={"python": "def solution(v1, v2):\n    p1 = [int(x) for x in v1.split('.')]\n    p2 = [int(x) for x in v2.split('.')]\n    if p1 > p2: return 1\n    elif p1 < p2: return -1\n    return 0\n"}, test_cases=[{"input_data": ["1.2.3", "1.2.4"], "expected_output": -1, "description": "Compare versions"}], time_limit_minutes=8),
            AssessmentQuestion(id="plt_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: CI Build Pipeline Duration & Success Metrics", prompt="Select repo_name and average build duration where status = 'success'.", starter_code={"sql": "SELECT repo_name, ROUND(AVG(duration_sec), 1) as avg_duration FROM build_jobs WHERE status = 'success' GROUP BY repo_name ORDER BY avg_duration ASC;\n"}, test_cases=[{"description": "Average build time", "setup_sql": "CREATE TABLE build_jobs (id INT, repo_name TEXT, duration_sec INT, status TEXT); INSERT INTO build_jobs VALUES (1, 'backend', 120, 'success'), (2, 'backend', 140, 'success'), (3, 'frontend', 60, 'success');", "expected_output": [["frontend", 60.0], ["backend", 130.0]]}], time_limit_minutes=8),
            AssessmentQuestion(id="plt_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Environment Variable Substitution Parser", prompt="Fix parser to substitute `${VAR}` with environment values.", starter_code={"python": "def solution(template, env_vars):\n    out = template\n    for k, v in env_vars.items():\n        out = out.replace(f'${{{k}}}', str(v))\n    return out\n"}, test_cases=[{"input_data": ["Server on ${HOST}:${PORT}", {"HOST": "localhost", "PORT": 8080}], "expected_output": "Server on localhost:8080", "description": "Substitute template variables"}], time_limit_minutes=8)
        ]
    }

    # 18. DATA SCIENTIST
    tracks["data_scientist"] = {
        "track_id": "data_scientist", "title": "Data Scientist (Statistical Modeling & A/B Testing)",
        "badge": "Stats & Modeling", "description": "p-values, statistical power, A/B test sample sizing, feature engineering, and logistic regression.",
        "skills": ["Python", "Statistics", "A/B Testing", "Scikit-Learn", "Pandas", "SQL"],
        "questions": [
            AssessmentQuestion(id="ds_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="A/B Testing: Type I vs Type II Error", prompt="In hypothesis testing, what is a Type I error (False Positive)?", options=["A) Rejecting the null hypothesis when it is actually true.", "B) Failing to reject null hypothesis when false.", "C) Dividing by standard error.", "D) Missing sample data."], correct_option=0, explanation="Type I error is concluding an effect exists when it does not.", time_limit_minutes=2),
            AssessmentQuestion(id="ds_mcq_2", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Overfitting Mitigation: L1 Lasso vs L2 Ridge", prompt="What unique structural effect does L1 Regularization (Lasso) have on model coefficients compared to L2 (Ridge)?", options=["A) L1 enforces exact zeros, performing automatic sparse feature selection.", "B) L1 multiplies weights by infinity.", "C) L1 prevents gradient descent.", "D) L1 only works on decision trees."], correct_option=0, explanation="L1 penalizes absolute magnitude, driving coefficients of non-informative features to zero.", time_limit_minutes=2),
            AssessmentQuestion(id="ds_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Data Science: Min-Max Feature Scaling Normalizer", prompt="Normalize a list of numbers to range [0, 1] using formula `(x - min) / (max - min)`.", starter_code={"python": "def solution(values):\n    mn = min(values); mx = max(values)\n    if mx == mn: return [0.0] * len(values)\n    return [round((x - mn) / (mx - mn), 2) for x in values]\n"}, test_cases=[{"input_data": [10, 20, 30], "expected_output": [0.0, 0.5, 1.0], "description": "Min-max normalization"}], time_limit_minutes=8),
            AssessmentQuestion(id="ds_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: A/B Test Variant Conversion Rate Comparison", prompt="Select variant and conversion rate % (`converted * 100.0 / total_users`) grouped by variant.", starter_code={"sql": "SELECT variant, ROUND((SUM(converted) * 100.0) / COUNT(*), 2) as conv_rate FROM ab_test_results GROUP BY variant ORDER BY conv_rate DESC;\n"}, test_cases=[{"description": "A/B test conversion", "setup_sql": "CREATE TABLE ab_test_results (id INT, variant TEXT, converted INT); INSERT INTO ab_test_results VALUES (1, 'A', 1), (2, 'A', 0), (3, 'B', 1), (4, 'B', 1);", "expected_output": [["B", 100.0], ["A", 50.0]]}], time_limit_minutes=8),
            AssessmentQuestion(id="ds_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Outlier Filter Standard Deviation Range", prompt="Filter values that lie beyond 2 standard deviations from the mean.", starter_code={"python": "import math\ndef solution(data):\n    mean = sum(data) / len(data)\n    std = math.sqrt(sum((x - mean) ** 2 for x in data) / len(data))\n    return [x for x in data if abs(x - mean) <= 2 * std]\n"}, test_cases=[{"input_data": [10, 12, 11, 100], "expected_output": [10, 12, 11], "description": "Filter outlier 100"}], time_limit_minutes=8)
        ]
    }

    # 19. API & ENTERPRISE INTEGRATIONS ENGINEER
    tracks["api_integrations_engineer"] = {
        "track_id": "api_integrations_engineer", "title": "API & Enterprise Integrations Engineer",
        "badge": "Integrations & OAuth", "description": "Webhook signature verification, OAuth2 PKCE, rate limiting, and enterprise data mapping.",
        "skills": ["REST", "OAuth2", "Webhooks", "JSON/XML", "Python", "SQL"],
        "questions": [
            AssessmentQuestion(id="api_mcq_1", type="mcq", modality="security_audit", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="OAuth 2.0 PKCE Security", prompt="Why is Proof Key for Code Exchange (PKCE) mandatory for public mobile and Single Page Applications (SPAs)?", options=["A) Public clients cannot securely maintain a client secret, and PKCE prevents authorization code interception attacks.", "B) PKCE speeds up database writes.", "C) PKCE disables CORS.", "D) PKCE replaces HTTPS with UDP."], correct_option=0, explanation="PKCE binds authorization codes to cryptographically generated code verifiers.", time_limit_minutes=2),
            AssessmentQuestion(id="api_mcq_2", type="mcq", modality="resilience_fault_tolerance", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Webhook Idempotency & Delivery Guarantees", prompt="Because webhooks operate with 'at-least-once' delivery guarantees, how must recipient systems process payloads?", options=["A) Reject duplicates with HTTP 500.", "B) Track unique webhook event IDs and process incoming payloads idempotently.", "C) Delete user database.", "D) Ignore all retries."], correct_option=1, explanation="At-least-once delivery requires idempotent consumers using unique event IDs.", time_limit_minutes=2),
            AssessmentQuestion(id="api_dsa_1", type="coding", modality="data_transformation", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Integrations: XML to JSON Key-Value Transformer", prompt="Transform flat key-value pairs into nested dictionary format.", starter_code={"python": "def solution(pairs):\n    d = {}\n    for k, v in pairs:\n        d[k] = v\n    return d\n"}, test_cases=[{"input_data": [[["name", "Acme"], ["id", "123"]]], "expected_output": {"name": "Acme", "id": "123"}, "description": "Map pairs to dict"}], time_limit_minutes=8),
            AssessmentQuestion(id="api_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: Webhook Delivery Status & Error Rate Audit", prompt="Select destination endpoint and count of failed deliveries where status = 'failed'.", starter_code={"sql": "SELECT endpoint_url, COUNT(*) as fail_count FROM webhook_events WHERE status = 'failed' GROUP BY endpoint_url ORDER BY fail_count DESC;\n"}, test_cases=[{"description": "Failed webhook audit", "setup_sql": "CREATE TABLE webhook_events (id INT, endpoint_url TEXT, status TEXT); INSERT INTO webhook_events VALUES (1, 'https://api.partner.com', 'failed'), (2, 'https://api.partner.com', 'failed'), (3, 'https://api.other.com', 'success');", "expected_output": [["https://api.partner.com", 2]]}], time_limit_minutes=8),
            AssessmentQuestion(id="api_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Webhook HMAC SHA256 Signature Verification", prompt="Fix signature generator so it digests byte payloads correctly with hmac sha256.", starter_code={"python": "import hmac, hashlib\ndef solution(secret, payload):\n    return hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()\n"}, test_cases=[{"input_data": ["my_secret", "{\"event\":\"ping\"}"], "expected_output": "9390299f1ca8bc7ae1da26b48598a69eb657b98d92976cb7cf161271f2fc3a86", "description": "Valid HMAC digest"}], time_limit_minutes=8)
        ]
    }

    # 20. GAME ENGINE & GRAPHICS DEVELOPER
    tracks["game_developer"] = {
        "track_id": "game_developer", "title": "Game Engine & Graphics Developer",
        "badge": "Game Dev & Physics", "description": "Fixed timestep physics loops, spatial partitioning (quadtrees), vertex shaders, and 2D/3D collision detection.",
        "skills": ["C++", "C#", "OpenGL/Vulkan", "Physics", "Math", "Python", "SQL"],
        "questions": [
            AssessmentQuestion(id="gm_mcq_1", type="mcq", modality="mcq_fundamentals", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Fixed Timestep Physics vs Variable Frame Rate", prompt="Why do physics engines update in a fixed timestep loop rather than variable delta time per frame?", options=["A) Variable time saves GPU memory.", "B) Fixed timestep guarantees deterministic physics calculations and prevents collision tunneling caused by frame drops.", "C) It limits maximum frames to 30.", "D) Monitors cannot display variable frames."], correct_option=1, explanation="Fixed dt prevents instability and guarantees deterministic simulation.", time_limit_minutes=2),
            AssessmentQuestion(id="gm_mcq_2", type="mcq", modality="mcq_architecture", section="mcq", section_title="Section 1: Multiple Choice Questions (MCQs)", title="Spatial Partitioning: Quadtree / Octree Acceleration", prompt="How does spatial partitioning reduce collision check complexity from O(N^2) to O(N log N)?", options=["A) Deleting off-screen objects.", "B) Dividing space hierarchically so objects only test collisions against entities occupying the same spatial cell.", "C) Disabling gravity.", "D) Shifting collision testing to audio thread."], correct_option=1, explanation="Hierarchical cells avoid checking distant non-intersecting entities.", time_limit_minutes=2),
            AssessmentQuestion(id="gm_dsa_1", type="coding", modality="dsa_algorithms", section="coding", section_title="Section 2: Coding & DSA Challenges", title="Game Math: 2D Circle Collision Detector", prompt="Detect if two circles intersect: distance between centers <= sum of radii. Return boolean.", starter_code={"python": "import math\ndef solution(c1, c2):\n    # c = [x, y, r]\n    dx = c1[0] - c2[0]\n    dy = c1[1] - c2[1]\n    dist = math.sqrt(dx * dx + dy * dy)\n    return dist <= (c1[2] + c2[2])\n"}, test_cases=[{"input_data": [[0, 0, 5], [6, 0, 2]], "expected_output": True, "description": "Circle collision test"}], time_limit_minutes=8),
            AssessmentQuestion(id="gm_sql_1", type="sql", modality="sql_aggregation_analytics", section="sql", section_title="Section 2: Interactive SQL & Data Challenges", title="SQL: Player Leaderboard High Scores", prompt="Select player_name and high_score for players with score >= 1000 ordered by score DESC.", starter_code={"sql": "SELECT player_name, MAX(score) as high_score FROM game_scores GROUP BY player_name HAVING MAX(score) >= 1000 ORDER BY high_score DESC;\n"}, test_cases=[{"description": "High score leaderboard", "setup_sql": "CREATE TABLE game_scores (id INT, player_name TEXT, score INT); INSERT INTO game_scores VALUES (1, 'PlayerOne', 1250), (2, 'PlayerOne', 900), (3, 'Noob', 400);", "expected_output": [["PlayerOne", 1250]]}], time_limit_minutes=8),
            AssessmentQuestion(id="gm_deb_1", type="debugging", modality="code_debugging", section="coding", section_title="Section 2: Code Debugging & Threat Defense", title="Debugging: Fix Frame Rate FPS Delta Time Clamping", prompt="Clamp delta time `dt` to `max_dt` so backgrounding application does not produce a huge physics explosion jump.", starter_code={"python": "def solution(raw_dt, max_dt):\n    return min(raw_dt, max_dt)\n"}, test_cases=[{"input_data": [0.5, 0.05], "expected_output": 0.05, "description": "Clamp spike dt"}], time_limit_minutes=8)
        ]
    }

    return tracks


# Merge the 20 roles together
EXAM_TRACKS_20.update(_build_remaining_15_roles())
