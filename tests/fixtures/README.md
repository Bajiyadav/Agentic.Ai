# Deterministic Test Fixtures Suite

This directory contains version-controlled, reproducible, synthetic test fixtures for AuditAgent screening verification.

## Directory Structure

```text
tests/fixtures/
├── resumes/
│   ├── valid_backend_engineer.pdf      # Valid candidate with Python, FastAPI, Docker, and GitHub
│   ├── valid_fullstack_engineer.pdf    # Valid candidate with React, TypeScript, Node.js, and GitHub
│   ├── valid_resume_no_github.pdf      # Valid candidate with Java, Spring Boot, but NO GitHub account
│   ├── valid_resume_with_experiment.pdf# Valid ML engineer with "experiment" mentions (A/B testing)
│   └── valid_low_score_resume.pdf      # Valid resume structure with poor match (tests score != validity)
│
├── invalid_documents/
│   ├── academic_lab_manual.pdf         # Coursework SQL lab instructions (halts at Doc Gate)
│   ├── coursework_assignment.pdf       # University homework assignment (halts at Doc Gate)
│   ├── question_paper.pdf              # University exam paper (halts at Doc Gate)
│   ├── unrelated_document.pdf          # Restaurant menu (halts at Doc Gate)
│   └── empty_document.pdf              # Text under 80 characters (halts at Doc Gate)
│
├── corrupted/
│   └── corrupt_pdf.pdf                 # Truncated raw stream missing %PDF- magic bytes
│
└── expected/
    └── screening_expectations.json     # Machine-readable expected business states
```

## Regeneration

All fixtures are 100% synthetic (zero candidate PII) and deterministic. To regenerate them:

```bash
.venv/bin/python tests/fixtures/generate_fixtures.py
```

## Test Usage

These fixtures are executed as part of the normal test suite in `tests/test_fixtures_matrix.py`:
- Validates that legitimate candidates receive valid assessments.
- Proves that invalid documents halt immediately without running GitHub or LLM evaluation.
- Enforces the critical rule: `overall_score == 0` does NOT imply `is_valid_resume == False`.
- Proves parity between single-resume screening and batch screening pipelines.
