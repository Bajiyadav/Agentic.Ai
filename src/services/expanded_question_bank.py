"""
Expanded 20-MCQ, 2-DSA, Debugging & SQL Question Bank Engine

Provides rich, production-grade technical challenges for all engineering tracks:
- 20 MCQs per track (10 Core Domain Fundamentals + 10 System Architecture & Concurrency)
- 2 Algorithmic DSA Coding Challenges with starter code & unit tests (visible + hidden)
- 1 Code Debugging Challenge (locating and repairing race conditions / logic defects)
- 1 Interactive SQL Database Query Challenge (evaluated in sandbox)
"""

from typing import Dict, Any, List
from .exam_catalog import AssessmentQuestion


def build_software_engineer_bank() -> List[AssessmentQuestion]:
    """Generates 20 MCQs + 2 DSA + 1 Debugging + 1 SQL for Software Engineer."""
    questions: List[AssessmentQuestion] = []
    
    # --- 10 FUNDAMENTALS MCQS ---
    fund_mcqs = [
        ("swe_mcq_f01", "PostgreSQL Transaction Isolation & SSI",
         "Which transaction isolation level in PostgreSQL guarantees Serializable Snapshot Isolation (SSI) to prevent write-skew anomalies without table-level locking?",
         ["A) Read Committed", "B) Repeatable Read", "C) Serializable", "D) Read Uncommitted"], 2,
         "PostgreSQL implements Serializable using SSI, detecting read-write conflict cycles without table locks.", 2),
        
        ("swe_mcq_f02", "Python Global Interpreter Lock (GIL) Concurrency",
         "In CPython, what is the exact effect of the GIL when executing CPU-bound threads versus I/O-bound threads?",
         ["A) CPU-bound threads run across all cores, while I/O threads share one core.",
          "B) Only one thread executes Python bytecode at a time, so CPU-bound parallelism requires multiprocessing, while I/O-bound threads release the GIL during syscalls.",
          "C) The GIL was completely eliminated in Python 3.8.",
          "D) The GIL only synchronizes asynchronous coroutines inside asyncio."], 1,
         "CPython's GIL restricts bytecode execution to one thread at a time, releasing during I/O operations.", 2),

        ("swe_mcq_f03", "TCP 3-Way Handshake & Connection States",
         "During a standard TCP connection termination, what is the purpose of the TIME_WAIT state on the active closer side?",
         ["A) To keep the socket open for immediate reuse by the next connection.",
          "B) To ensure the remote host received the final ACK and to allow lingering delayed segments to dissipate.",
          "C) To encrypt the payload before discarding socket buffers.",
          "D) To renegotiate TCP window size parameters."], 1,
         "TIME_WAIT (typically 2*MSL) prevents old duplicate packets from interfering with new connections on the same port.", 2),

        ("swe_mcq_f04", "B-Tree vs Hash Index Performance Characteristics",
         "Why do production relational databases like PostgreSQL choose B-Tree indexes as the default over Hash indexes?",
         ["A) Hash indexes take O(N) space, while B-Trees take O(1) space.",
          "B) B-Trees efficiently support range queries (<, <=, BETWEEN) and ordering (ORDER BY), whereas Hash indexes only support exact equality (=).",
          "C) Hash indexes cannot be stored on disk.",
          "D) B-Tree indexes guarantee O(1) search time in all cases."], 1,
         "B-Tree preserves sorted order, enabling range scans, prefix searches, and sorting.", 2),

        ("swe_mcq_f05", "HTTP/2 Multiplexing vs HTTP/1.1 Pipelining",
         "What fundamental architectural enhancement does HTTP/2 introduce over HTTP/1.1 to solve Head-of-Line (HoL) blocking at the application layer?",
         ["A) It switches application transport to UDP datagrams exclusively.",
          "B) It breaks requests and responses into binary frames multiplexed over a single TCP connection stream.",
          "C) It prohibits keep-alive connections.",
          "D) It compresses request bodies with gzip."], 1,
         "HTTP/2 multiplexes interleaved binary frames across independent streams over a single connection.", 2),

        ("swe_mcq_f06", "Memory Hierarchy & CPU Cache Lines",
         "What is false sharing in multi-threaded concurrent programming?",
         ["A) Threads attempting to read memory allocated in a different operating system process.",
          "B) Independent variables modified by different threads residing on the same CPU cache line (e.g. 64 bytes), causing continuous invalidation.",
          "C) Threads sharing garbage collection pointers across different runtimes.",
          "D) A hardware defect where RAM fails to store parity bits."], 1,
         "False sharing occurs when independent variables on the same cache line force cache invalidation cycles.", 2),

        ("swe_mcq_f07", "Linux File Descriptor & Epoll Scalability",
         "Why does Linux `epoll` scale to tens of thousands of concurrent connections (C10K) while `select` degrades significantly with connection count?",
         ["A) `select` uses kernel threads, while `epoll` runs purely in user space.",
          "B) `select` requires scanning the entire O(N) file descriptor array on every poll, while `epoll` uses event callbacks in an O(1) ready list.",
          "C) `epoll` disables TCP checksumming for high throughput.",
          "D) `select` can only listen on UDP sockets."], 1,
         "epoll uses an event-driven callback mechanism, returning only active sockets in O(active) rather than iterating O(total).", 2),

        ("swe_mcq_f08", "Database Normalization & 3NF Invariants",
         "A relational table satisfies Third Normal Form (3NF) if and only if it is in 2NF and what condition holds?",
         ["A) Every non-key attribute is non-transitively dependent on the primary key (no X -> Y where Y -> Z).",
          "B) It contains no foreign key relationships.",
          "C) Every column contains comma-separated values.",
          "D) All tables have exactly three columns."], 0,
         "3NF requires that no non-prime attribute is transitively dependent on any candidate key.", 2),

        ("swe_mcq_f09", "Deadlock Conditions (Coffman Invariants)",
         "Which of the following is NOT one of the four necessary Coffman conditions required for a deadlock to occur in a concurrent system?",
         ["A) Mutual Exclusion", "B) Hold and Wait", "C) Preemption Permitted", "D) Circular Wait"], 2,
         "No preemption (resources cannot be forcibly reclaimed) is required for deadlock; preemption prevents deadlock.", 2),

        ("swe_mcq_f10", "REST Idempotency Semantics",
         "According to RFC 9110 HTTP Semantics, which HTTP methods are defined as both idempotent and safe by standard?",
         ["A) POST and PATCH", "B) GET and HEAD", "C) PUT and DELETE", "D) POST and DELETE"], 1,
         "GET and HEAD are both safe (read-only without server state modification) and idempotent.", 2),
    ]

    for qid, title, prompt, opts, correct, expl, t_lim in fund_mcqs:
        questions.append(AssessmentQuestion(
            id=qid,
            type="mcq",
            modality="mcq_fundamentals",
            section="mcq",
            section_title="Section 1: Multiple Choice Questions (MCQs)",
            title=title,
            prompt=prompt,
            options=opts,
            correct_option=correct,
            explanation=expl,
            time_limit_minutes=t_lim
        ))

    # --- 10 ARCHITECTURE MCQS ---
    arch_mcqs = [
        ("swe_mcq_a01", "Distributed CAP Theorem & PACELC Trade-offs",
         "In a distributed data store experiencing network partitions, according to the PACELC theorem, what trade-off must be evaluated when no partition is present?",
         ["A) Durability vs Encryption", "B) Latency vs Consistency", "C) Throughput vs Disk space", "D) Memory vs Bandwidth"], 1,
         "PACELC states: if Partition (P), choose Availability (A) or Consistency (C); Else (E), choose Latency (L) or Consistency (C).", 2),

        ("swe_mcq_a02", "Event-Driven Message Delivery Semantics",
         "In an event-driven system with Apache Kafka or RabbitMQ, how does an engineering team guarantee exactly-once processing (EOS) end-to-end?",
         ["A) Relying solely on TCP packet acknowledgments.",
          "B) Combining at-least-once message delivery with idempotent consumer handlers or unique transaction dedup keys.",
          "C) Setting consumer concurrency to 0.",
          "D) Disabling message acknowledgment retries entirely."], 1,
         "At-least-once delivery paired with idempotent state mutations or deduplication tables achieves effective exactly-once semantics.", 2),

        ("swe_mcq_a03", "Cache Stampede & Dogpiling Prevention",
         "When a high-traffic cache key expires simultaneously for thousands of concurrent requests, which strategy prevents database overload (cache stampede)?",
         ["A) Setting TTL to 0 for all keys.",
          "B) Using probabilistic early expiration (XFetch) or mutex locking so only one worker recomputes the cache entry.",
          "C) Restarting the Redis instance periodically.",
          "D) Storing cache values in plain text files."], 1,
         "Mutex locking or probabilistic early expiration (XFetch algorithm) ensures only a single request queries the DB upon expiration.", 2),

        ("swe_mcq_a04", "Database Read Replicas & Replication Lag",
         "A user updates their profile and immediately refreshes the page, but observes stale data. What architectural pattern resolves this Read-Your-Own-Writes lag?",
         ["A) Route read requests for the recently updated user to the primary database for a short grace window (e.g. 5 seconds).",
          "B) Disable read replicas and scale the primary vertically.",
          "C) Introduce a random delay sleep on all user browser clicks.",
          "D) Cache the entire database in localStorage."], 0,
         "Routing reads to the primary immediately following a write (or using replication timestamp tracking) ensures Read-Your-Own-Writes consistency.", 2),

        ("swe_mcq_a05", "Distributed Consensus & Raft Leader Election",
         "In the Raft consensus algorithm, how is split-vote deadlocks resolved during leader election?",
         ["A) Manual operator intervention.",
          "B) Randomized election timeouts across candidate nodes (e.g. 150-300ms).",
          "C) The node with the largest IP address automatically assumes leadership.",
          "D) Consensus switches to Paxos temporarily."], 1,
         "Randomized election timeouts ensure one node times out and initiates election before competitors, preventing persistent split votes.", 2),

        ("swe_mcq_a06", "Microservices Saga Pattern vs Two-Phase Commit",
         "Why is the Saga pattern preferred over Two-Phase Commit (2PC) in modern distributed microservice architectures across disparate cloud providers?",
         ["A) 2PC is faster than local in-memory transactions.",
          "B) 2PC is a blocking protocol that holds locks across network boundaries, creating availability bottlenecks and single points of failure.",
          "C) Sagas do not require compensating transactions.",
          "D) 2PC cannot be implemented in any relational database."], 1,
         "2PC holds locks across network boundaries, drastically reducing availability and throughput in distributed systems.", 2),

        ("swe_mcq_a07", "Rate Limiting: Token Bucket vs Fixed Window Counter",
         "What is the primary operational weakness of a Fixed Window Counter rate limiter that Token Bucket and Sliding Window Logs solve?",
         ["A) Fixed Window counters consume too much memory.",
          "B) Double the permitted request burst can pass through at window boundary transitions (e.g. end of minute N and start of minute N+1).",
          "C) Fixed Window counters cannot be implemented in Redis.",
          "D) Token Bucket counters require persistent disk I/O on every request."], 1,
         "Boundary bursts allow 2x traffic spikes across the window edge in fixed window counter designs.", 2),

        ("swe_mcq_a08", "Database Sharding & Consistent Hashing",
         "What is the primary benefit of Consistent Hashing with virtual nodes when distributing keys across database shards?",
         ["A) It guarantees that all keys are encrypted.",
          "B) When adding or removing a shard, only K/N keys need to be remapped on average, avoiding massive cluster rehashing.",
          "C) It allows sharding without primary keys.",
          "D) It converts all queries into single-table lookups."], 1,
         "Consistent hashing limits rebalancing overhead to K/N keys when cluster nodes join or leave.", 2),

        ("swe_mcq_a09", "Resilience & Circuit Breaker Pattern",
         "In the Netflix Hystrix / Resilience4j Circuit Breaker model, what initiates the transition from OPEN to HALF-OPEN state?",
         ["A) All downstream services returning HTTP 200.",
          "B) Expiration of a configured sleep window timer, allowing a limited trial batch of probe requests through.",
          "C) Manual reset by a DevOps engineer.",
          "D) Immediate retry on the next incoming request."], 1,
         "After an open timeout elapses, the circuit transitions to half-open to test if downstream health has recovered.", 2),

        ("swe_mcq_a10", "Zero-Downtime Database Migration (Expand & Contract)",
         "When renaming a production database column used by high-throughput APIs without downtime, what is the correct sequence in the Expand/Contract pattern?",
         ["A) Drop old column -> Deploy new code -> Add new column.",
          "B) Add new column -> Dual-write to both -> Backfill historical data -> Switch reads to new column -> Stop writing to old column -> Drop old column.",
          "C) Stop the database server for 30 minutes during maintenance.",
          "D) Use an ALTER TABLE RENAME COLUMN query during peak business hours."], 1,
         "Expand/Contract (Parallel Run) adds the new column, dual-writes, backfills, switches consumers, and finally cleans up the obsolete column.", 2),
    ]

    for qid, title, prompt, opts, correct, expl, t_lim in arch_mcqs:
        questions.append(AssessmentQuestion(
            id=qid,
            type="mcq",
            modality="mcq_architecture",
            section="mcq",
            section_title="Section 1: Multiple Choice Questions (MCQs)",
            title=title,
            prompt=prompt,
            options=opts,
            correct_option=correct,
            explanation=expl,
            time_limit_minutes=t_lim
        ))

    # --- 2 DSA CHALLENGES ---
    # DSA Challenge 1: Two Sum / Target Pair Finder
    questions.append(AssessmentQuestion(
        id="swe_dsa_1",
        type="coding",
        modality="dsa_algorithms",
        section="coding",
        section_title="Section 2: Algorithmic Coding (DSA)",
        title="DSA Problem 1: Optimal Target Sum Pair Finder (O(N) Time)",
        prompt=(
            "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n"
            "Assumptions:\n"
            "- Each input has exactly one solution, and you may not use the same element twice.\n"
            "- You must return the indices in ascending order.\n"
            "- Expected Time Complexity: O(N), Space Complexity: O(N)."
        ),
        starter_code={
            "python": (
                "def solution(nums, target):\n"
                "    # Return list of two indices [i, j] adding to target\n"
                "    seen = {}\n"
                "    for i, num in enumerate(nums):\n"
                "        comp = target - num\n"
                "        if comp in seen:\n"
                "            return [seen[comp], i]\n"
                "        seen[num] = i\n"
                "    return []\n"
            )
        },
        test_cases=[
            {"input_data": [[2, 7, 11, 15], 9], "expected_output": [0, 1], "description": "Basic pair at start"},
            {"input_data": [[3, 2, 4], 6], "expected_output": [1, 2], "description": "Pair in middle/end"},
            {"input_data": [[3, 3], 6], "expected_output": [0, 1], "description": "Identical values duplicate check"},
            {"input_data": [[1, 5, 8, 12, 19, 25], 37], "expected_output": [3, 4], "description": "Higher values hidden test", "hidden": True}
        ],
        time_limit_minutes=15
    ))

    # DSA Challenge 2: Longest Substring Without Repeating Characters (Sliding Window)
    questions.append(AssessmentQuestion(
        id="swe_dsa_2",
        type="coding",
        modality="dsa_algorithms",
        section="coding",
        section_title="Section 2: Algorithmic Coding (DSA)",
        title="DSA Problem 2: Longest Substring Without Repeating Characters",
        prompt=(
            "Given a string `s`, find the length of the longest substring without duplicate characters.\n"
            "Examples:\n"
            "- `s = \"abcabcbb\"` -> Returns `3` (\"abc\")\n"
            "- `s = \"bbbbb\"` -> Returns `1` (\"b\")\n"
            "- `s = \"pwwkew\"` -> Returns `3` (\"wke\")\n"
            "Constraints:\n"
            "- Time Complexity: O(N) using sliding window.\n"
            "- Space Complexity: O(min(N, M)) where M is alphabet size."
        ),
        starter_code={
            "python": (
                "def solution(s):\n"
                "    # Return maximum length integer\n"
                "    char_map = {}\n"
                "    left = 0\n"
                "    max_len = 0\n"
                "    for right, char in enumerate(s):\n"
                "        if char in char_map and char_map[char] >= left:\n"
                "            left = char_map[char] + 1\n"
                "        char_map[char] = right\n"
                "        max_len = max(max_len, right - left + 1)\n"
                "    return max_len\n"
            )
        },
        test_cases=[
            {"input_data": ["abcabcbb"], "expected_output": 3, "description": "Standard alternating string"},
            {"input_data": ["bbbbb"], "expected_output": 1, "description": "All repeated characters"},
            {"input_data": ["pwwkew"], "expected_output": 3, "description": "Substring with duplicate ahead"},
            {"input_data": [""], "expected_output": 0, "description": "Empty string edge case"},
            {"input_data": ["tmmzuxt"], "expected_output": 5, "description": "Complex duplicate boundary", "hidden": True}
        ],
        time_limit_minutes=20
    ))

    # --- 1 DEBUGGING CHALLENGE ---
    questions.append(AssessmentQuestion(
        id="swe_debug_1",
        type="debugging",
        modality="code_debugging",
        section="coding",
        section_title="Section 2: Hands-On Debugging Challenges",
        title="Debugging: Fix Sliding Window Rate Limiter Boundary Off-By-One",
        prompt=(
            "The following rate limiter allows requests if the count within `window_seconds` does not exceed `max_requests`.\n"
            "However, it contains an off-by-one boundary defect where old timestamps are not properly purged before checking capacity, "
            "and requests on the exact boundary are improperly rejected.\n"
            "Fix the logic in `allow_request(timestamps, current_time, window_seconds, max_requests)` to return `True` when permitted and `False` otherwise."
        ),
        starter_code={
            "python": (
                "def solution(timestamps, current_time, window_seconds, max_requests):\n"
                "    cutoff = current_time - window_seconds\n"
                "    # Bug: using <= cutoff instead of < cutoff leaves exact-boundary items\n"
                "    valid = [t for t in timestamps if t > cutoff]\n"
                "    if len(valid) < max_requests:\n"
                "        return True\n"
                "    return False\n"
            )
        },
        test_cases=[
            {"input_data": [[10, 20, 30], 40, 30, 3], "expected_output": False, "description": "At max capacity 3 items within window"},
            {"input_data": [[10, 20], 40, 25, 3], "expected_output": True, "description": "Item 10 is outside window 40-25=15; only 1 item remaining"},
            {"input_data": [[], 100, 60, 5], "expected_output": True, "description": "Empty timestamps initial request"}
        ],
        time_limit_minutes=10
    ))

    # --- 1 SQL CHALLENGE ---
    questions.append(AssessmentQuestion(
        id="swe_sql_1",
        type="sql",
        modality="sql_window_cte",
        section="sql",
        section_title="Section 2: Interactive Database & SQL Challenges",
        title="SQL: Department Top 2 Salaries via DENSE_RANK()",
        prompt=(
            "Write a SQL query to find employees who have the top 2 highest salaries in each department.\n"
            "Return: `department_name`, `employee_name`, `salary`, `salary_rank` ordered by `department_name` ASC, `salary_rank` ASC."
        ),
        db_schema_setup=(
            "CREATE TABLE departments (id INT PRIMARY KEY, name VARCHAR(50));\n"
            "CREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(50), salary INT, department_id INT);\n"
            "INSERT INTO departments VALUES (1, 'Engineering'), (2, 'Sales');\n"
            "INSERT INTO employees VALUES (101, 'Alice', 120000, 1), (102, 'Bob', 110000, 1), (103, 'Charlie', 110000, 1), (104, 'David', 90000, 1), (105, 'Eve', 95000, 2), (106, 'Frank', 95000, 2), (107, 'Grace', 80000, 2);\n"
        ),
        starter_code={
            "sql": (
                "WITH Ranked AS (\n"
                "    SELECT d.name AS department_name, e.name AS employee_name, e.salary,\n"
                "           DENSE_RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) as salary_rank\n"
                "    FROM employees e\n"
                "    JOIN departments d ON e.department_id = d.id\n"
                ")\n"
                "SELECT department_name, employee_name, salary, salary_rank\n"
                "FROM Ranked\n"
                "WHERE salary_rank <= 2\n"
                "ORDER BY department_name ASC, salary_rank ASC, employee_name ASC;\n"
            )
        },
        test_cases=[
            {
                "input_data": [],
                "expected_output": [
                    {"department_name": "Engineering", "employee_name": "Alice", "salary": 120000, "salary_rank": 1},
                    {"department_name": "Engineering", "employee_name": "Bob", "salary": 110000, "salary_rank": 2},
                    {"department_name": "Engineering", "employee_name": "Charlie", "salary": 110000, "salary_rank": 2},
                    {"department_name": "Sales", "employee_name": "Eve", "salary": 95000, "salary_rank": 1},
                    {"department_name": "Sales", "employee_name": "Frank", "salary": 95000, "salary_rank": 1}
                ],
                "description": "Dense rank preserves ties accurately"
            }
        ],
        time_limit_minutes=10
    ))

    return questions


def build_data_engineer_bank() -> List[AssessmentQuestion]:
    """Generates 20 MCQs + 2 DSA + 1 Debugging + 1 SQL for Data Engineer."""
    questions: List[AssessmentQuestion] = []
    
    # 10 Fundamentals
    de_f = [
        ("de_mcq_f01", "Columnar vs Row-Oriented Storage Layout",
         "Why do analytical warehouses (Parquet, BigQuery, ClickHouse) achieve superior performance on aggregation queries over row stores (PostgreSQL, MySQL)?",
         ["A) Columnar stores load entire rows into memory for all queries.",
          "B) Columnar stores only read the specific columns requested from disk and leverage high compression ratios on homogenous data types.",
          "C) Columnar stores prohibit data partitioning.",
          "D) Columnar stores eliminate the need for primary keys."], 1,
         "Columnar formats minimize I/O by reading only required attributes and compressing identical columnar data.", 2),

        ("de_mcq_f02", "Apache Spark Shuffle & Partitions",
         "What occurs in Apache Spark when an operation like `groupByKey()` or `join()` triggers a Wide Dependency transformation?",
         ["A) Spark executes the operation in L1 cache on the driver without network transfer.",
          "B) Spark performs a cluster-wide shuffle, serializing, partitioning, and transmitting data across executors over the network.",
          "C) Spark converts RDDs into pandas DataFrames.",
          "D) The job fails with an OutOfMemory error immediately."], 1,
         "Wide transformations require data to be partitioned and shuffled across worker nodes.", 2),

        ("de_mcq_f03", "Data Lakehouse: ACID Transactions on Object Storage",
         "How do table formats like Apache Iceberg, Delta Lake, and Apache Hudi achieve ACID transactions on eventually consistent object storage like Amazon S3 or Google Cloud Storage?",
         ["A) By placing an in-memory Redis lock on every file.",
          "B) Using atomic metadata commit manifests (JSON/Avro) with snapshot isolation and optimistic concurrency control (OCC).",
          "C) Re-writing the entire data bucket on every INSERT.",
          "D) Disabling concurrent writers at the DNS level."], 1,
         "Table formats write immutable Parquet files and commit atomic snapshots via metadata trees.", 2),

        ("de_mcq_f04", "Kafka Log Compaction Mechanics",
         "In Apache Kafka, what does enabling Log Compaction (`cleanup.policy=compact`) guarantee for a topic?",
         ["A) Messages are deleted exactly 7 days after insertion.",
          "B) Kafka retains at least the last known value for each message key within the log partition.",
          "C) All message payloads are compressed using gzip on disk.",
          "D) Consumers receive messages in reverse chronological order."], 1,
         "Log compaction retains the latest record value per key, enabling changelog state recovery.", 2),

        ("de_mcq_f05", "Slowly Changing Dimensions (SCD Type 2)",
         "In dimensional data modeling, how does an SCD Type 2 table track historical attribute modifications (e.g. customer address updates)?",
         ["A) Overwriting the existing row with new values.",
          "B) Inserting a new version row with effective start/end timestamps and an `is_current` boolean flag.",
          "C) Appending the old value to a JSON column array.",
          "D) Dropping the customer record and creating a new ID."], 1,
         "SCD Type 2 preserves historical changes by inserting versioned records with validity timestamps.", 2),

        ("de_mcq_f06", "Partition Skew & Salting Technique",
         "In distributed ETL processing (Spark/Flink), what is the 'salting' technique used to remediate join/grouping data skew?",
         ["A) Encrypting sensitive column values with salt hashes.",
          "B) Appending a pseudo-random integer to skewed keys to distribute records evenly across partition buckets, then stripping the salt after the join.",
          "C) Filtering out null values from the join.",
          "D) Increasing executor RAM to 1 Terabyte."], 1,
         "Key salting breaks heavy skewed keys into sub-keys, balancing data across partitions.", 2),

        ("de_mcq_f07", "Watermarking in Stream Processing",
         "What is the purpose of a Watermark in streaming engines like Apache Flink or Spark Structured Streaming?",
         ["A) To watermark images for copyright verification.",
          "B) To establish a temporal threshold declaring that no event data with timestamps earlier than the watermark will arrive, allowing event-time window state to be finalized.",
          "C) To measure network bandwidth latency.",
          "D) To trigger garbage collection in the JVM."], 1,
         "Watermarks tell the stream processor how late data can arrive before an event-time window is closed.", 2),

        ("de_mcq_f08", "Airflow DAG Best Practices & Top-Level Code",
         "Why should Apache Airflow DAG files strictly avoid heavy computation or external database connections at the top-level scope outside operator execute methods?",
         ["A) Python does not allow top-level code.",
          "B) The Airflow Scheduler parses DAG files continuously every few seconds, causing severe database connection starvation and scheduler latency spikes.",
          "C) External connections are blocked by Airflow security.",
          "D) Operators cannot inherit top-level variables."], 1,
         "The scheduler parses DAGs repeatedly; top-level DB or network calls create connection exhaustion and scheduler lockup.", 2),

        ("de_mcq_f09", "Snowflake Micro-Partitioning & Pruning",
         "How does Snowflake achieve fast query execution on multi-terabyte tables without requiring manual index creation?",
         ["A) By creating B-Tree indexes on every column automatically.",
          "B) By partitioning data into immutable 50MB-500MB micro-partitions and maintaining min/max metadata per column for partition pruning.",
          "C) By storing all data in memory uncompressed.",
          "D) By converting all SQL queries into map-reduce jobs."], 1,
         "Snowflake automatically micro-partitions tables and uses columnar min/max metadata to prune non-matching partitions.", 2),

        ("de_mcq_f10", "CDC (Change Data Capture) via Debezium",
         "What is the operational advantage of log-based Change Data Capture (e.g. Debezium reading PostgreSQL WAL or MySQL binlog) over query-based polling (SELECT WHERE updated_at > t)?",
         ["A) Log-based CDC captures DELETE operations and transaction boundaries with zero query overhead on the application database.",
          "B) Query-based polling consumes less network bandwidth.",
          "C) Log-based CDC does not require database permissions.",
          "D) Query-based polling guarantees sub-millisecond latency."], 0,
         "Log-based CDC extracts all mutations (including hard deletes) directly from storage write-ahead logs without polling query load.", 2),
    ]

    for qid, title, prompt, opts, correct, expl, t_lim in de_f:
        questions.append(AssessmentQuestion(
            id=qid, type="mcq", modality="mcq_fundamentals", section="mcq",
            section_title="Section 1: Multiple Choice Questions (MCQs)",
            title=title, prompt=prompt, options=opts, correct_option=correct,
            explanation=expl, time_limit_minutes=t_lim
        ))

    # 10 Architecture
    de_a = [
        ("de_mcq_a01", "Lambda vs Kappa Architecture Trade-offs",
         "Why do modern real-time data engineering teams frequently adopt the Kappa Architecture over the Lambda Architecture?",
         ["A) Kappa architecture relies on batch processing only.",
          "B) Kappa eliminates the requirement to maintain two separate codebases and processing engines (batch + speed layers), using a single stream processing engine for both real-time and historical backfills.",
          "C) Lambda architecture cannot be hosted on cloud infrastructure.",
          "D) Kappa architecture does not require persistent storage."], 1,
         "Kappa architecture simplifies operations by utilizing a single stream processing framework for both real-time streams and replayable historical logs.", 2),

        ("de_mcq_a02", "Idempotent Data Lakehouse Ingestion",
         "What pattern guarantees exactly-once writes when loading streaming micro-batches into an Iceberg or Delta Lake table?",
         ["A) Appending rows continuously without checking batch IDs.",
          "B) Writing to staging Parquet files and committing with an atomic MERGE or transactional overwrite based on batch sequence identifiers.",
          "C) Dropping the destination table before every insert.",
          "D) Relying on TCP socket reliability."], 1,
         "Atomic MERGE / overwrite keyed on batch idempotency tokens guarantees exact single delivery into Lakehouse tables.", 2),

        ("de_mcq_a03", "Data Quality Gates: Great Expectations in CI/CD",
         "In an enterprise ELT pipeline, what is the best practice for executing automated Data Contracts and schema assertions?",
         ["A) Evaluating schema assertions directly in production after users report discrepancies.",
          "B) Running automated validation tests (e.g. null checks, uniqueness, range bounds) in a staging layer before promoting data to production presentation marts.",
          "C) Disabling null checks for performance.",
          "D) Relying on BI dashboards to alert on anomalies."], 1,
         "Staging quality gates prevent corrupt or malformed records from polluting downstream production consumption layers.", 2),

        ("de_mcq_a04", "Kafka Backpressure & Consumer Lag Handling",
         "When a Kafka consumer group experiences escalating consumer lag due to slow downstream database writes, which architectural action resolves the bottleneck without message loss?",
         ["A) Deleting unconsumed messages from the Kafka broker.",
          "B) Increasing the partition count and adding consumer worker instances up to the partition count, paired with micro-batching bulk database writes.",
          "C) Disabling consumer offset commits.",
          "D) Increasing producer polling timeouts."], 1,
         "Scaling partition counts and matching consumer workers alongside bulk database inserts accelerates consumption throughput.", 2),

        ("de_mcq_a05", "Event-Time vs Processing-Time Temporal Alignment",
         "In a financial fraud detection pipeline, why is joining events on Event Time mandatory rather than Processing Time?",
         ["A) Processing time is faster to compute.",
          "B) Network latency and ingestion delays cause events to arrive out of order; processing time would evaluate events under incorrect temporal state.",
          "C) Event time is only available on iOS devices.",
          "D) Processing time cannot be stored in timestamps."], 1,
         "Event time reflects the true chronological occurrence of actions regardless of transmission or processing jitter.", 2),

        ("de_mcq_a06", "Broadcast Hash Join vs Sort-Merge Join in Spark",
         "When joining a 10TB facts table with a 50MB dimension lookup table in Spark, why is a Broadcast Hash Join (BHJ) vastly superior to a Sort-Merge Join?",
         ["A) BHJ writes the entire 10TB table to local disk.",
          "B) The 50MB dimension table is broadcast to all executor nodes, eliminating cluster-wide network shuffle of the 10TB fact table.",
          "C) BHJ converts SQL into map-reduce.",
          "D) Sort-merge joins cannot join integer keys."], 1,
         "Broadcasting small lookup tables avoids costly cluster-wide network shuffling of massive fact datasets.", 2),

        ("de_mcq_a07", "Zero-Copy Data Sharing: Arrow Flight & Parquet",
         "How does Apache Arrow drastically reduce latency when transferring data between Python, Spark, and C++ analytical runtimes?",
         ["A) By converting tabular records into JSON strings.",
          "B) By utilizing a standardized columnar in-memory layout that enables zero-copy reads without serialization/deserialization CPU overhead.",
          "C) By encrypting memory pointers.",
          "D) By writing records to temporary SQLite files."], 1,
         "Arrow standardizes columnar memory representation, eliminating serialization penalties across languages.", 2),

        ("de_mcq_a08", "Dead-Letter Queue (DLQ) in Streaming Pipelines",
         "When a streaming consumer encounters a malformed 'poison pill' record that fails schema validation, what is the fault-tolerant design pattern?",
         ["A) Crash the worker process immediately and stop the pipeline.",
          "B) Route the offending message alongside metadata/error stacks to a Dead-Letter Queue (DLQ) topic and continue consuming valid stream traffic.",
          "C) Silently discard the message without logging.",
          "D) Restart the Kafka broker cluster."], 1,
         "DLQ routing quarantines corrupted records for offline inspection while maintaining real-time stream processing continuity.", 2),

        ("de_mcq_a09", "Data Warehouse Tiering: Medallion Architecture",
         "In Databricks / Lakehouse Medallion Architecture (Bronze -> Silver -> Gold), what represents the Gold tier?",
         ["A) Raw unaltered ingested payloads.",
          "B) Cleaned, validated, and normalized dimensional models and aggregated business marts ready for executive BI and ML consumption.",
          "C) Deprecated backup files.",
          "D) In-memory cache indexes only."], 1,
         "Gold tier contains curated, aggregated business-level tables optimized for reporting and analytics.", 2),

        ("de_mcq_a10", "Parquet Compaction & Small Files Problem",
         "What negative operational symptom occurs when an ETL pipeline writes thousands of tiny 50KB Parquet files to S3, and how is it resolved?",
         ["A) Cloud storage runs out of inodes; solved by switching to FTP.",
          "B) Massive object listing metadata latency and slow query scan times; solved by running scheduled bin-packing file compaction jobs (e.g. OPTIMIZE).",
          "C) Data becomes permanently corrupt.",
          "D) AWS S3 rejects file reads over 100 files."], 1,
         "Thousands of small files generate excessive HTTP metadata overhead; compaction jobs combine them into optimal 128MB-512MB sizes.", 2),
    ]

    for qid, title, prompt, opts, correct, expl, t_lim in de_a:
        questions.append(AssessmentQuestion(
            id=qid, type="mcq", modality="mcq_architecture", section="mcq",
            section_title="Section 1: Multiple Choice Questions (MCQs)",
            title=title, prompt=prompt, options=opts, correct_option=correct,
            explanation=expl, time_limit_minutes=t_lim
        ))

    # 2 DSA Challenges
    # DSA 1: Top K Frequent Stream Elements
    questions.append(AssessmentQuestion(
        id="de_dsa_1",
        type="coding",
        modality="dsa_algorithms",
        section="coding",
        section_title="Section 2: Algorithmic Coding (DSA)",
        title="DSA Problem 1: Top K Frequent Elements in Event Stream",
        prompt=(
            "Given an integer array `nums` and an integer `k`, return the `k` most frequent elements in descending order of frequency.\n"
            "Must achieve better than O(N log N) time complexity (e.g. O(N log K) using min-heap or O(N) using bucket sort)."
        ),
        starter_code={
            "python": (
                "import collections\n"
                "import heapq\n\n"
                "def solution(nums, k):\n"
                "    # Return list of top k elements\n"
                "    count = collections.Counter(nums)\n"
                "    return [item[0] for item in heapq.nlargest(k, count.items(), key=lambda x: x[1])]\n"
            )
        },
        test_cases=[
            {"input_data": [[1, 1, 1, 2, 2, 3], 2], "expected_output": [1, 2], "description": "Basic top 2"},
            {"input_data": [[1], 1], "expected_output": [1], "description": "Single element"},
            {"input_data": [[4, 4, 4, 4, 5, 5, 6], 1], "expected_output": [4], "description": "Dominant item", "hidden": True}
        ],
        time_limit_minutes=15
    ))

    # DSA 2: Merge Overlapping Time Intervals
    questions.append(AssessmentQuestion(
        id="de_dsa_2",
        type="coding",
        modality="dsa_algorithms",
        section="coding",
        section_title="Section 2: Algorithmic Coding (DSA)",
        title="DSA Problem 2: Merge Overlapping Data Ingestion Windows",
        prompt=(
            "Given an array of time intervals `intervals` where `intervals[i] = [start_i, end_i]`,\n"
            "merge all overlapping intervals and return an array of the non-overlapping intervals that cover all intervals in the input.\n"
            "Example: `[[1,3],[2,6],[8,10],[15,18]]` -> `[[1,6],[8,10],[15,18]]`."
        ),
        starter_code={
            "python": (
                "def solution(intervals):\n"
                "    if not intervals:\n"
                "        return []\n"
                "    intervals.sort(key=lambda x: x[0])\n"
                "    merged = [intervals[0]]\n"
                "    for current in intervals[1:]:\n"
                "        prev = merged[-1]\n"
                "        if current[0] <= prev[1]:\n"
                "            prev[1] = max(prev[1], current[1])\n"
                "        else:\n"
                "            merged.append(current)\n"
                "    return merged\n"
            )
        },
        test_cases=[
            {"input_data": [[[1, 3], [2, 6], [8, 10], [15, 18]]], "expected_output": [[1, 6], [8, 10], [15, 18]], "description": "Overlapping start ranges"},
            {"input_data": [[[1, 4], [4, 5]]], "expected_output": [[1, 5]], "description": "Adjacent touching boundary"},
            {"input_data": [[[6, 8], [1, 9], [2, 4]]], "expected_output": [[1, 9]], "description": "Completely enclosing interval", "hidden": True}
        ],
        time_limit_minutes=20
    ))

    # Debugging Challenge
    questions.append(AssessmentQuestion(
        id="de_debug_1",
        type="debugging",
        modality="code_debugging",
        section="coding",
        section_title="Section 2: Hands-On Debugging Challenges",
        title="Debugging: Fix Memory Leak in Streaming Micro-Batch Deduplicator",
        prompt=(
            "The following function processes batches of event IDs and records seen keys in a set to avoid processing duplicates.\n"
            "However, the cache set grows unbounded without an eviction strategy, causing OutOfMemory errors in long-running stream workers.\n"
            "Implement a maximum size bounded deduplication window (`max_keys`) that discards oldest keys when capacity is reached."
        ),
        starter_code={
            "python": (
                "from collections import OrderedDict\n\n"
                "def solution(event_stream, max_capacity):\n"
                "    seen = OrderedDict()\n"
                "    processed = []\n"
                "    for event_id in event_stream:\n"
                "        if event_id not in seen:\n"
                "            seen[event_id] = True\n"
                "            processed.append(event_id)\n"
                "            if len(seen) > max_capacity:\n"
                "                seen.popitem(last=False)\n"
                "    return processed\n"
            )
        },
        test_cases=[
            {"input_data": [[1, 2, 3, 2, 4, 1, 5], 3], "expected_output": [1, 2, 3, 4, 1, 5], "description": "Evicts 1 so 1 can be re-seen after capacity"},
            {"input_data": [[10, 10, 10, 20], 5], "expected_output": [10, 20], "description": "Duplicate rejection"}
        ],
        time_limit_minutes=10
    ))

    # SQL Challenge
    questions.append(AssessmentQuestion(
        id="de_sql_1",
        type="sql",
        modality="sql_window_cte",
        section="sql",
        section_title="Section 2: Interactive Database & SQL Challenges",
        title="SQL: Calculate 7-Day Moving Average Daily Active Users",
        prompt=(
            "Write a SQL query to calculate the 7-day moving average of daily active users (DAU).\n"
            "Return: `activity_date`, `daily_users`, and `moving_avg_7d` rounded to 1 decimal place."
        ),
        db_schema_setup=(
            "CREATE TABLE daily_metrics (activity_date DATE PRIMARY KEY, daily_users INT);\n"
            "INSERT INTO daily_metrics VALUES ('2024-01-01', 100), ('2024-01-02', 120), ('2024-01-03', 110), ('2024-01-04', 130), ('2024-01-05', 140), ('2024-01-06', 150), ('2024-01-07', 160), ('2024-01-08', 170);\n"
        ),
        starter_code={
            "sql": (
                "SELECT activity_date, daily_users,\n"
                "       ROUND(AVG(daily_users) OVER (\n"
                "           ORDER BY activity_date\n"
                "           ROWS BETWEEN 6 PRECEDING AND CURRENT ROW\n"
                "       ), 1) AS moving_avg_7d\n"
                "FROM daily_metrics\n"
                "ORDER BY activity_date ASC;\n"
            )
        },
        test_cases=[
            {
                "input_data": [],
                "expected_output": [
                    {"activity_date": "2024-01-01", "daily_users": 100, "moving_avg_7d": 100.0},
                    {"activity_date": "2024-01-02", "daily_users": 120, "moving_avg_7d": 110.0},
                    {"activity_date": "2024-01-03", "daily_users": 110, "moving_avg_7d": 110.0},
                    {"activity_date": "2024-01-04", "daily_users": 130, "moving_avg_7d": 115.0},
                    {"activity_date": "2024-01-05", "daily_users": 140, "moving_avg_7d": 120.0},
                    {"activity_date": "2024-01-06", "daily_users": 150, "moving_avg_7d": 125.0},
                    {"activity_date": "2024-01-07", "daily_users": 160, "moving_avg_7d": 130.0},
                    {"activity_date": "2024-01-08", "daily_users": 170, "moving_avg_7d": 140.0}
                ],
                "description": "7-day sliding window bounds"
            }
        ],
        time_limit_minutes=10
    ))

    return questions


def get_expanded_track_questions(track_id: str) -> List[AssessmentQuestion]:
    """Retrieves the full 20 MCQ + 2 DSA + Debugging + SQL catalog for the given track."""
    if track_id == "data_engineer":
        return build_data_engineer_bank()
    # Default to Software Engineer / Backend (or customized per track)
    return build_software_engineer_bank()
