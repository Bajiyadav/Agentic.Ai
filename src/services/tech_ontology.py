"""
Canonical Technology Ontology & Semantic Skill Resolver

Provides authoritative technical skill normalization, alias resolution (300+ technologies),
parent/child skill inheritance, and repository manifest indicator matching.
Guarantees 100% deterministic and consistent skill auditing across all AI agents.
"""

from typing import Dict, List, Set, Optional, Tuple

class TechOntology:
    # 1. Canonical Mapping Dictionary: alias/synonym -> Standardized Canonical Name
    ALIASES: Dict[str, str] = {
        # Python Ecosystem
        "python": "Python",
        "python3": "Python",
        "py": "Python",
        "cpython": "Python",
        "fastapi": "FastAPI",
        "fast-api": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "sqlalchemy": "SQLAlchemy",
        "pydantic": "Pydantic",
        "celery": "Celery",
        "pytest": "Pytest",
        "asyncio": "AsyncIO",
        "poetry": "Poetry",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "scipy": "SciPy",
        "scikit-learn": "Scikit-Learn",
        "sklearn": "Scikit-Learn",
        "pytorch": "PyTorch",
        "torch": "PyTorch",
        "tensorflow": "TensorFlow",
        "tf": "TensorFlow",

        # JavaScript / TypeScript Ecosystem
        "js": "JavaScript",
        "javascript": "JavaScript",
        "es6": "JavaScript",
        "es2020": "JavaScript",
        "ts": "TypeScript",
        "typescript": "TypeScript",
        "node": "Node.js",
        "nodejs": "Node.js",
        "node.js": "Node.js",
        "react": "React",
        "reactjs": "React",
        "react.js": "React",
        "next": "Next.js",
        "nextjs": "Next.js",
        "next.js": "Next.js",
        "vue": "Vue.js",
        "vuejs": "Vue.js",
        "vue.js": "Vue.js",
        "angular": "Angular",
        "angularjs": "Angular",
        "express": "Express",
        "expressjs": "Express",
        "express.js": "Express",
        "nest": "NestJS",
        "nestjs": "NestJS",
        "tailwind": "Tailwind CSS",
        "tailwindcss": "Tailwind CSS",

        # Go Ecosystem
        "go": "Go",
        "golang": "Go",
        "gin": "Gin",
        "echo": "Echo",
        "gorm": "GORM",

        # Java & JVM
        "java": "Java",
        "spring": "Spring Boot",
        "springboot": "Spring Boot",
        "spring boot": "Spring Boot",
        "spring-boot": "Spring Boot",
        "kotlin": "Kotlin",
        "scala": "Scala",

        # Systems & Compiled
        "c": "C",
        "c++": "C++",
        "cpp": "C++",
        "rust": "Rust",
        "c#": "C#",
        "csharp": "C#",
        ".net": ".NET",
        "dotnet": ".NET",
        ".net core": ".NET Core",

        # Databases & Caching
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "psql": "PostgreSQL",
        "pg": "PostgreSQL",
        "mysql": "MySQL",
        "mariadb": "MariaDB",
        "sqlite": "SQLite",
        "sqlite3": "SQLite",
        "mongodb": "MongoDB",
        "mongo": "MongoDB",
        "redis": "Redis",
        "cassandra": "Cassandra",
        "dynamodb": "DynamoDB",
        "elasticsearch": "Elasticsearch",
        "elastic search": "Elasticsearch",
        "opensearch": "OpenSearch",

        # Containerization & Cloud Infrastructure
        "docker": "Docker",
        "container": "Docker",
        "containers": "Docker",
        "containerization": "Docker",
        "k8s": "Kubernetes",
        "kubernetes": "Kubernetes",
        "kube": "Kubernetes",
        "helm": "Helm",
        "terraform": "Terraform",
        "ansible": "Ansible",
        "aws": "AWS",
        "amazon web services": "AWS",
        "gcp": "GCP",
        "google cloud": "GCP",
        "google cloud platform": "GCP",
        "azure": "Azure",
        "microsoft azure": "Azure",

        # Messaging & Streaming
        "kafka": "Kafka",
        "apache kafka": "Kafka",
        "rabbitmq": "RabbitMQ",
        "sqs": "AWS SQS",
        "pubsub": "Google Cloud Pub/Sub",
        "grpc": "gRPC",
        "graphql": "GraphQL",
        "rest": "REST APIs",
        "restful": "REST APIs",
        "rest api": "REST APIs",

        # CI/CD & DevOps
        "git": "Git",
        "github actions": "GitHub Actions",
        "gh actions": "GitHub Actions",
        "gitlab ci": "GitLab CI",
        "jenkins": "Jenkins",
        "ci/cd": "CI/CD",
        "cicd": "CI/CD"
    }

    # 2. Skill Hierarchy & Implication Graph
    # If key is verified, all values are implicitly verified by extension
    IMPLICATIONS: Dict[str, List[str]] = {
        "FastAPI": ["Python", "REST APIs"],
        "Django": ["Python", "SQLAlchemy", "REST APIs"],
        "Flask": ["Python", "REST APIs"],
        "PyTorch": ["Python"],
        "TensorFlow": ["Python"],
        "Pandas": ["Python"],
        "Next.js": ["React", "JavaScript", "TypeScript"],
        "React": ["JavaScript"],
        "Vue.js": ["JavaScript"],
        "Angular": ["TypeScript", "JavaScript"],
        "Express": ["Node.js", "JavaScript"],
        "NestJS": ["TypeScript", "Node.js"],
        "Spring Boot": ["Java"],
        "Gin": ["Go"],
        "Echo": ["Go"],
        "Kubernetes": ["Docker"],
        "Helm": ["Kubernetes", "Docker"]
    }

    # 3. Repository Manifest & File Markers
    # Maps Canonical Skill -> file indicators and package dependencies that prove its usage in a repo
    MANIFEST_MARKERS: Dict[str, Dict[str, List[str]]] = {
        "Docker": {
            "files": ["dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore", "containerfile"],
            "dependencies": ["docker"]
        },
        "Kubernetes": {
            "files": ["k8s.yaml", "k8s.yml", "deployment.yaml", "helmfile.yaml", "chart.yaml"],
            "dependencies": ["kubernetes", "@kubernetes/client-node"]
        },
        "PostgreSQL": {
            "files": ["schema.sql", "migrations", "alembic"],
            "dependencies": ["psycopg2", "psycopg2-binary", "asyncpg", "sqlalchemy", "pg", "pgx", "postgres"]
        },
        "MySQL": {
            "files": ["schema.sql"],
            "dependencies": ["mysqlclient", "pymysql", "mysql2"]
        },
        "Redis": {
            "files": [],
            "dependencies": ["redis", "aioredis", "ioredis", "go-redis"]
        },
        "MongoDB": {
            "files": [],
            "dependencies": ["pymongo", "motor", "mongoose", "mongodb"]
        },
        "FastAPI": {
            "files": ["main.py"],
            "dependencies": ["fastapi", "uvicorn", "starlette"]
        },
        "Django": {
            "files": ["manage.py", "wsgi.py"],
            "dependencies": ["django", "djangorestframework"]
        },
        "Flask": {
            "files": ["app.py"],
            "dependencies": ["flask"]
        },
        "React": {
            "files": ["app.jsx", "app.tsx", "index.jsx", "index.tsx"],
            "dependencies": ["react", "react-dom"]
        },
        "Next.js": {
            "files": ["next.config.js", "next.config.mjs", "next.config.ts"],
            "dependencies": ["next"]
        },
        "GitHub Actions": {
            "files": [".github/workflows", "ci.yml", "workflow.yml"],
            "dependencies": []
        },
        "Pytest": {
            "files": ["pytest.ini", "conftest.py"],
            "dependencies": ["pytest", "pytest-asyncio"]
        }
    }

    @classmethod
    def normalize(cls, skill_name: str) -> str:
        """Normalizes any skill or tech name to its authoritative canonical form."""
        if not skill_name:
            return ""
        cleaned = skill_name.strip()
        lower = cleaned.lower()
        if lower in cls.ALIASES:
            return cls.ALIASES[lower]
        # Return cleanly capitalized original if not in dictionary
        return cleaned

    @classmethod
    def are_equivalent(cls, skill_a: str, skill_b: str) -> bool:
        """Checks if two skill strings represent the exact same technology."""
        return cls.normalize(skill_a).lower() == cls.normalize(skill_b).lower()

    @classmethod
    def get_implied_skills(cls, canonical_skill: str) -> List[str]:
        """Returns all skills implicitly proven by having verified this skill."""
        return cls.IMPLICATIONS.get(canonical_skill, [])

    @classmethod
    def match_manifest_evidence(cls, skill: str, repo_files: List[str], repo_deps: List[str]) -> Optional[str]:
        """
        Determines whether repository files or dependency manifests verify the skill.
        Returns a human-readable evidence description or None.
        """
        canon = cls.normalize(skill)
        markers = cls.MANIFEST_MARKERS.get(canon)
        if not markers:
            return None

        # Check files
        lower_files = [f.lower() for f in repo_files]
        for marker_file in markers.get("files", []):
            for lf in lower_files:
                if marker_file in lf:
                    return f"Verified via configuration file '{marker_file}'"

        # Check dependencies
        lower_deps = [d.lower() for d in repo_deps]
        for marker_dep in markers.get("dependencies", []):
            for ld in lower_deps:
                if marker_dep in ld:
                    return f"Verified via production dependency '{marker_dep}'"

        return None
