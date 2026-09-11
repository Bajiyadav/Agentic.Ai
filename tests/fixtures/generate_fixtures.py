#!/usr/bin/env python3
"""
Deterministic Test Fixture Generator for AuditAgent.
Generates synthetic PDFs for reproducible unit, integration, and CI testing.
Zero candidate PII. All data is purely synthetic and deterministic.
"""

import os
import io
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

FIXTURES_DIR = Path(__file__).parent.resolve()
RESUMES_DIR = FIXTURES_DIR / "resumes"
INVALID_DIR = FIXTURES_DIR / "invalid_documents"
CORRUPTED_DIR = FIXTURES_DIR / "corrupted"
EXPECTED_DIR = FIXTURES_DIR / "expected"

def _make_pdf(filepath: Path, text: str) -> None:
    """Writes a standard deterministic PDF file from text."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    textobject = c.beginText(50, 750)
    for line in text.strip().split("\n"):
        textobject.textLine(line.strip())
    c.drawText(textobject)
    c.showPage()
    c.save()
    with open(filepath, "wb") as f:
        f.write(buf.getvalue())

def generate_all_fixtures() -> None:
    """Generates all synthetic test fixtures."""
    # 1. Valid Backend Engineer Resume
    backend_resume = """
    Alex Mercer
    Email: alex.mercer@testmail.local | Phone: (555) 123-4567
    GitHub: github.com/alexmercer | LinkedIn: linkedin.com/in/alexmercer

    Professional Summary:
    Senior Backend Software Engineer with 5+ years of experience designing scalable microservices,
    distributed message queues, and high-performance REST APIs in cloud environments.

    Technical Skills:
    Languages: Python, Go, SQL
    Frameworks: FastAPI, Flask, Django
    Tools & Infrastructure: Docker, PostgreSQL, Redis, Kubernetes, AWS, Git

    Work Experience:
    Senior Software Engineer - CloudData Solutions (2021 - Present)
    - Architected distributed data ingestion pipelines processing 10M+ events daily with FastAPI and Kafka.
    - Optimized PostgreSQL query indexes, reducing latency by 45%.
    - Containerized microservices using Docker and orchestrated deployments on Kubernetes.

    Software Engineer - FinTech Labs (2019 - 2021)
    - Developed payment gateway integrations with Python and Redis caching.
    - Wrote comprehensive unit and integration test suites with 92% code coverage.

    Education:
    B.S. in Computer Science - Tech University (2015 - 2019)
    """
    _make_pdf(RESUMES_DIR / "valid_backend_engineer.pdf", backend_resume)

    # 2. Valid Fullstack Engineer Resume
    fullstack_resume = """
    Jordan Taylor
    Email: jordan.taylor@testmail.local | Phone: (555) 987-6543
    GitHub: github.com/jordantaylor | LinkedIn: linkedin.com/in/jordantaylor

    Professional Summary:
    Fullstack Engineer with 4 years of experience delivering reactive web applications and scalable APIs.

    Technical Skills:
    Languages: TypeScript, JavaScript, Python
    Frameworks: React, Next.js, Node.js, Express
    Tools & Databases: PostgreSQL, TailwindCSS, Docker, Git, Jest

    Work Experience:
    Fullstack Developer - WebSphere Digital (2020 - Present)
    - Built responsive React and Next.js customer portals with server-side rendering.
    - Designed RESTful API services in Node.js and TypeScript connected to PostgreSQL.
    - Implemented CI/CD pipelines with automated testing and Docker builds.

    Education:
    B.S. in Software Engineering - State Institute (2016 - 2020)
    """
    _make_pdf(RESUMES_DIR / "valid_fullstack_engineer.pdf", fullstack_resume)

    # 3. Valid Resume Without GitHub
    no_github_resume = """
    David Vance
    Email: david.vance@testmail.local | Phone: (555) 456-7890
    LinkedIn: linkedin.com/in/davidvance

    Professional Summary:
    Enterprise Backend Engineer with 6 years of experience in financial systems and enterprise integrations.

    Technical Skills:
    Languages: Java, SQL, Python
    Frameworks: Spring Boot, Hibernate
    Tools: AWS, Docker, Jenkins, PostgreSQL, Git

    Work Experience:
    Staff Backend Engineer - LegacyFin Corp (2018 - Present)
    - Architected secure payment ledger processing systems using Spring Boot and PostgreSQL.
    - Managed multi-region database replication and automated failover.
    - Led architecture review board for enterprise API security standards.

    Education:
    M.S. in Information Systems - Global Tech University (2016 - 2018)
    B.S. in Computer Engineering - State University (2012 - 2016)
    """
    _make_pdf(RESUMES_DIR / "valid_resume_no_github.pdf", no_github_resume)

    # 4. Valid Resume With "Experiment" Mentions (A/B testing, ML experiments)
    experiment_resume = """
    Elena Rostova
    Email: elena.rostova@testmail.local | Phone: (555) 321-7654
    GitHub: github.com/elenarostova | LinkedIn: linkedin.com/in/elenarostova

    Professional Summary:
    Machine Learning Engineer with 5 years of experience leading statistical experimentation and predictive modeling.

    Technical Skills:
    Languages: Python, C++, SQL
    Frameworks: PyTorch, Scikit-Learn, FastAPI
    Tools: MLflow, Docker, Kubernetes, AWS, Git

    Work Experience:
    Machine Learning Engineer - Predictive AI Labs (2020 - Present)
    - Designed and launched 40+ production A/B experiment iterations for recommendation engines.
    - Built automated experiment tracking pipelines using MLflow, Docker, and PyTorch.
    - Published research experiments on transformer model compression and inference optimization.
    - Analyzed multi-variant user experiments to optimize conversion funnels.

    Education:
    M.S. in Computer Science - State Tech University (2018 - 2020)
    B.S. in Mathematics and Statistics (2014 - 2018)
    """
    _make_pdf(RESUMES_DIR / "valid_resume_with_experiment.pdf", experiment_resume)

    # 5. Valid Low-Quality / Low-Score Candidate Resume (Valid structure, but poor engineering match)
    low_score_resume = """
    Kevin Miller
    Email: kevin.miller@testmail.local | Phone: (555) 555-0199
    Address: 123 Maple Street, Smallville

    Professional Summary:
    General assistant looking for entry-level opportunities in technical environments.

    Experience:
    IT Support Assistant - City Library (2022 - 2023)
    - Managed printer paper refills and basic workstation power cables.
    - Assisted public visitors with browser navigation and password resets.

    Skills:
    Customer Service, Microsoft Word, Data Entry, Email

    Education:
    High School Diploma - Smallville High School (2021)
    """
    _make_pdf(RESUMES_DIR / "valid_low_score_resume.pdf", low_score_resume)

    # 6. Academic Lab Manual
    lab_manual = """
    Course Code: CS301 Database Management Systems Laboratory
    Experiment # 2: Types of Constraints in Relational Databases
    Department of Computer Science and Engineering
    Semester: Fall 2024

    Aim:
    To write and execute SQL commands to demonstrate PRIMARY KEY, FOREIGN KEY, UNIQUE, and CHECK constraints.

    Instructions:
    This document provides the SQL commands and expected outcomes for each lab exercise.
    You should execute these commands in your SQL environment (MySQL / PostgreSQL) and observe the results.

    Procedure:
    Step 1: Create table department with primary key dept_id.
    Step 2: Create table employee with foreign key dept_id references department.
    Step 3: Insert valid records and verify integrity constraint violations.

    Expected Outcomes:
    Integrity constraint check fails on foreign key mismatch.
    """
    _make_pdf(INVALID_DIR / "academic_lab_manual.pdf", lab_manual)

    # 7. Coursework Assignment
    assignment = """
    Course Code: CS204 Advanced Algorithms and Data Structures
    Assignment # 3: Graph Traversal and Dynamic Programming
    Department of Computer Science
    Semester: Spring 2024

    Instructions:
    Answer all 5 questions. Late submissions will receive a 20% penalty per day.
    Submit your code implementations along with mathematical complexity proofs.

    Question 1:
    Implement Dijkstra shortest path algorithm using a Fibonacci heap.
    Expected output should demonstrate O(V log V + E) asymptotic complexity.

    Question 2:
    Provide dynamic programming formulation for 0/1 Knapsack problem with runtime analysis.
    """
    _make_pdf(INVALID_DIR / "coursework_assignment.pdf", assignment)

    # 8. Question Paper
    question_paper = """
    Midterm Examination - Fall Semester 2024
    Course Code: IT302 Database Systems Architecture
    Question Paper
    Department of Information Technology
    Time Allowed: 3 Hours
    Total Marks: 100
    Marking Scheme: Section A (40 marks), Section B (60 marks)

    Section A:
    1. Define ACID properties with transactional examples.
    2. Explain the difference between B-Tree and B+ Tree indexing structures.

    Section B:
    3. Normalize the given schema to Boyce-Codd Normal Form (BCNF).
    """
    _make_pdf(INVALID_DIR / "question_paper.pdf", question_paper)

    # 9. Unrelated Document
    unrelated_doc = """
    The Daily Roast Cafe & Bistro - Lunch Menu
    Open Monday to Friday 8:00 AM - 4:00 PM

    Appetizers:
    - Artisan Garlic Bread with Herb Butter
    - Roasted Tomato and Basil Bruschetta
    - Seasonal Garden Salad with House Vinaigrette

    Main Courses:
    - Pan-Seared Atlantic Salmon with Asparagus
    - Wild Mushroom Risotto with Truffle Oil
    - Grilled Chicken Panini with Pesto Aioli

    Desserts:
    - Classic Tiramisu
    - Flourless Dark Chocolate Cake
    """
    _make_pdf(INVALID_DIR / "unrelated_document.pdf", unrelated_doc)

    # 10. Empty / Unreadable Document (<80 chars)
    empty_doc = "Hello world."
    _make_pdf(INVALID_DIR / "empty_document.pdf", empty_doc)

    # 11. Corrupted File (Not starting with %PDF-)
    CORRUPTED_DIR.mkdir(parents=True, exist_ok=True)
    corrupt_file = CORRUPTED_DIR / "corrupt_pdf.pdf"
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_VALID_PDF_STREAM_RANDOM_CORRUPT_BYTES_0987654321")

    print(f"✅ Successfully generated all test fixtures in {FIXTURES_DIR}")

if __name__ == "__main__":
    generate_all_fixtures()
