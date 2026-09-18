# AuditAgent Legal & Regulatory Compliance Framework

## Executive Compliance Statement
AuditAgent is architected from the ground up to comply with global employment, civil rights, and artificial intelligence regulations governing automated hiring decision tools, including **NYC Local Law 144 (AEDT)**, **EEOC Title VII / UGESP**, **California FEHA**, and **GDPR / EU AI Act**.

---

## 1. NYC Local Law 144 (Automated Employment Decision Tools - AEDT)

New York City Local Law 144 mandates that automated employment decision tools (AEDT) used to screen candidates for employment must satisfy three core statutory requirements:
1. Annual Independent Bias Audit
2. Public Summary of Bias Audit Results
3. Candidate Notice & Alternative Evaluation Procedures

### A. Independent Bias Audit & Impact Ratios
The platform calculates selection rates and **Adverse Impact Ratios (AIR)** across protected demographic groups (Sex/Gender, Race/Ethnicity, and Intersectional categories) following the official NYC Department of Consumer and Worker Protection (DCWP) rules:

$$\text{Selection Rate} = \frac{\text{Number of Candidates Selected / Recommended}}{\text{Total Number of Applicants in Demographic Group}}$$

$$\text{Impact Ratio (AIR)} = \frac{\text{Selection Rate of Protected Group}}{\text{Selection Rate of Most Selected Group}}$$

Under the standard **Four-Fifths (80%) Rule**:
- An Impact Ratio of **0.80 or greater** indicates no adverse impact.
- An Impact Ratio below **0.80** flags a potential disparate impact trigger, initiating an immediate algorithmic review.

### B. 10-Business-Day Advance Candidate Notice
Before screening any applicant using automated AI scoring, employers must provide clear written notice at least **10 business days** prior to evaluation:
- Notice must inform the candidate that an automated tool will assess their credentials.
- Notice must state the specific job qualifications and characteristics the tool assesses (e.g. programming languages, architecture, coding assessment results).
- The notice provides a direct link to the employer’s AEDT policy and data retention schedule.

### C. Accommodation & Alternative Evaluation Workflow
Candidates who cannot participate in automated code audits or proctored assessments due to disabilities or protected circumstances are entitled to request an alternative evaluation method:
- The candidate portal includes a prominent **"Request Alternative Assessment"** button.
- Triggering this halts automated scoring and assigns the application directly to a human recruiter for manual review without penalty.

---

## 2. EEOC Title VII & UGESP Compliance

Under the Equal Employment Opportunity Commission (EEOC) and the **Uniform Guidelines on Employee Selection Procedures (UGESP)**, automated evaluation tools must demonstrate **job-relatedness** and **business necessity**.

### A. Criterion-Related and Content Validity
- **Direct Skill Measurement**: Assessments only measure skills explicitly declared in the Job Opening's approved Job Description (`required_skills`).
- **No Hallucinated Criteria**: If a Job Description requires Python and PostgreSQL, the engine is mathematically barred from assessing or penalizing a candidate on AWS, Rust, or C++ (`Anti-Hallucination Gate`).
- **Standardized Rubrics**: Evaluation scores (0-100) are generated through deterministic rubrics and canonical technology matching, eliminating subjective recruiter bias.

### B. Safe Neutral Baselines (No Unfair Penalties)
- Many highly qualified engineers work under enterprise non-disclosure agreements (NDAs) or on proprietary enterprise systems without public GitHub portfolios.
- **Rule**: When a candidate has no public GitHub profile, their status is classified as `Unavailable` with the explanation:
  > *"GitHub profile unavailable; evaluated on resume claims alone. (Note: Enterprise engineering is frequently performed in private repositories)."*
- The platform **never assigns a zero score or auto-rejects** a candidate simply for lacking public open-source code.

### C. Elimination of Demographic Proxies
The resume parser strictly strips or ignores non-job-related attributes before score calculation:
- Candidate profile photos, gender pronouns, and age indicators.
- Graduation years older than 10 years (preventing age discrimination).
- Physical addresses (preventing zip-code/socio-economic proxy discrimination).

---

## 3. GDPR & International Privacy Standards

### A. Article 22: Automated Individual Decision-Making Safeguards
Under GDPR Article 22, individuals have the right not to be subject to decisions based solely on automated processing that produce legal effects.

AuditAgent adheres to Article 22 through:
1. **Decision Support, Not Decision Automation**: AuditAgent provides a *recommendation* and *scorecard* to the hiring manager; final employment decisions (interview invitations, rejections, offers) always require human authorization.
2. **Right to Explanation**: The platform generates explicit, human-readable rationales for every sub-score:
   - *"Candidate verified across 6 public repositories with 24 stars."*
   - *"Dockerfile and requirements.txt confirm practical containerization and database driver mastery."*
   - *"Lacks public code evidence for required skill 'Kubernetes'."*
3. **Human-in-the-Loop Anomaly Gate**: If the consensus evaluator detects high multi-evaluator score variance (> 20 points), the tool forces a `needs_manual_review = True` hold, preventing automated routing.

### B. Articles 15 & 17: Right of Access and Right to Erasure ("Right to Be Forgotten")
- **Candidate Data Export API**: Candidates can download all extracted claims, audited code snippets, assessment responses, and scores in structured JSON format.
- **Automated Data Purge API**:
  ```http
  DELETE /api/v1/candidates/{candidate_id}
  ```
  Completely anonymizes or hard-deletes candidate PII, resume files, and assessment proctoring logs while preserving aggregated, anonymized demographic counts for annual bias audits.

---

## 4. Cryptographic Audit Trail & Tamper Prevention

Every evaluation event is recorded in the `audit_logs` table with an immutable, cryptographically chained hash:

```python
audit_entry = {
    "organization_id": org_id,
    "event_type": "CANDIDATE_SCREENED",
    "timestamp": "2026-09-14T14:30:00Z",
    "details": {
        "candidate_id": cand_id,
        "overall_score": 85,
        "recommendation": "STRONG_CANDIDATE"
    },
    "prev_hash": previous_entry_hash,
    "current_hash": sha256_digest(...)
}
```

Any retrospective tampering or deletion of logs breaks the hash chain, providing verifiable audit readiness for independent compliance auditors and regulatory bodies.
