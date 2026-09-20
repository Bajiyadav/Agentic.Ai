import os
import re
import json
from uuid import UUID
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import CandidateAssessment, Candidate, JobOpening
from src.services.proctoring_service import ProctoringService
from src.services.exam_catalog import (
    AssessmentQuestion,
    EXAM_TRACKS_20 as EXAM_TRACKS,
    QUESTION_MODALITIES,
)
from src.services.campus_assessment_catalog import CAMPUS_GRADUATE_TRACK

class AssessmentPackage(BaseModel):
    job_title: str
    duration_minutes: int
    total_questions: int
    questions: List[AssessmentQuestion]

class AssessmentEvaluationResult(BaseModel):
    score: int = Field(ge=0, le=100)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str


def get_exam_tracks_meta() -> List[Dict[str, Any]]:
    """Returns summary metadata for all exam tracks including Campus & Graduate track."""
    tracks_meta = [
        {
            "track_id": data["track_id"],
            "title": data["title"],
            "badge": data["badge"],
            "description": data["description"],
            "skills": data["skills"],
            "total_questions": len(data["questions"]),
            "duration_minutes": 30,
            "challenge_types": [
                "Multiple Choice (MCQ - Core Concepts)",
                "Multiple Choice (MCQ - Architecture)",
                "Coding & DSA Challenge",
                "Interactive SQL Query Challenge",
                "Code Debugging & Threat Defense Challenge"
            ],
            "sections": [
                "Section 1: Multiple Choice Questions (MCQs)",
                "Section 2: Hands-On Challenges (Coding, SQL & Debugging)"
            ]
        }
        for data in EXAM_TRACKS.values()
    ]
    # Add specialized Campus & Graduate Hire track
    tracks_meta.append({
        "track_id": CAMPUS_GRADUATE_TRACK["track_id"],
        "title": CAMPUS_GRADUATE_TRACK["title"],
        "badge": CAMPUS_GRADUATE_TRACK["badge"],
        "description": CAMPUS_GRADUATE_TRACK["description"],
        "skills": CAMPUS_GRADUATE_TRACK["skills"],
        "total_questions": len(CAMPUS_GRADUATE_TRACK["questions"]),
        "duration_minutes": CAMPUS_GRADUATE_TRACK["duration_minutes"],
        "challenge_types": [
            "English Comprehension (Vocabulary, Grammar & Reading)",
            "Logical Ability (Deductive, Syllogisms & Puzzles)",
            "Quantitative Ability (Arithmetic, Algebra & Percentages)",
            "Data Structures (Arrays, Trees, Graphs, Sorting & Complexity)"
        ],
        "sections": CAMPUS_GRADUATE_TRACK["sections"],
        "section_breakdown": CAMPUS_GRADUATE_TRACK["section_breakdown"]
    })
    return tracks_meta


def get_question_modalities() -> List[Dict[str, str]]:
    """Returns the 10 customizable question modalities available across the platform."""
    return QUESTION_MODALITIES


def get_questions_for_track(track_id: str) -> List[AssessmentQuestion]:
    """Retrieve full AssessmentQuestion objects for the specified track."""
    if track_id == "campus_graduate_engineer":
        return list(CAMPUS_GRADUATE_TRACK["questions"])
    track = EXAM_TRACKS.get(track_id) or EXAM_TRACKS.get("software_engineer")
    return list(track["questions"])


def detect_exam_track(job_title: str, required_skills: Optional[List[str]] = None) -> str:
    """Infers the most appropriate exam track from job title and required skills across roles."""
    t = (job_title or "").lower()
    s = [x.lower() for x in (required_skills or [])]

    # Campus & Graduate Trainee detection
    if any(k in t for k in ["graduate", "campus", "entry level", "entry-level", "fresher", "intern", "junior", "trainee", "associate software engineer", "associate engineer"]):
        return "campus_graduate_engineer"
    if any(k in s for k in ["aptitude", "quantitative ability", "logical reasoning", "english comprehension", "campus hiring"]):
        return "campus_graduate_engineer"

    # Specific role checks
    if any(k in t for k in ["blockchain", "web3", "solidity", "smart contract", "crypto", "ethereum", "defi"]):
        return "blockchain_engineer"
    if any(k in t for k in ["embedded", "firmware", "iot", "rtos", "microcontroller", "hardware"]):
        return "embedded_iot_engineer"
    if any(k in t for k in ["nlp", "llm", "large language model", "rag", "genai"]):
        return "nlp_engineer"
    if any(k in t for k in ["computer vision", "vision", "opencv", "yolo", "cnn", "image processing"]):
        return "computer_vision_engineer"
    if any(k in t for k in ["dba", "database administrator", "database engineer", "postgres admin", "oracle"]):
        return "database_administrator"
    if any(k in t for k in ["cloud architect", "solutions architect", "enterprise architect", "aws architect"]):
        return "cloud_architect"
    if any(k in t for k in ["platform", "developer experience", "internal platform", "gitops"]):
        return "platform_engineer"
    if any(k in t for k in ["data scientist", "data science", "statistician", "econometrician"]):
        return "data_scientist"
    if any(k in t for k in ["integration engineer", "api engineer", "partner engineer", "solutions engineer"]):
        return "api_integrations_engineer"
    if any(k in t for k in ["game", "game developer", "graphics", "unreal", "unity", "vulkan", "shader"]):
        return "game_developer"
    if any(k in t for k in ["soc", "threat intelligence", "threat hunter", "incident response", "siem analyst", "forensic"]):
        return "cybersecurity_analyst"
    if any(k in t for k in ["security", "cyber", "infosec", "appsec", "penetration"]):
        return "security_engineer"
    if any(k in t for k in ["network", "bgp", "cisco", "juniper", "switch", "routing", "router"]):
        return "network_engineer"
    if any(k in t for k in ["mlops", "aiops", "triton", "model serving", "feature store"]):
        return "aiops_mlops_engineer"
    if any(k in t for k in ["big data", "lakehouse", "iceberg", "delta lake", "spark architect"]):
        return "big_data_architect"
    if any(k in t for k in ["salesforce", "apex", "crm", "servicenow", "soql"]):
        return "crm_enterprise_developer"
    if any(k in t for k in ["ar/vr", "xr", "webxr", "spatial", "virtual reality", "augmented reality"]):
        return "ar_vr_engineer"
    if any(k in t for k in ["quant", "fintech", "hft", "trading", "fix protocol", "order book"]):
        return "fintech_quant_developer"
    if any(k in t for k in ["bioinformatics", "genomics", "computational biology", "dna", "fastq"]):
        return "bioinformatics_engineer"
    if any(k in t for k in ["robotics", "autonomous", "ros", "ros 2", "lidar", "slam", "kalman"]):
        return "robotics_autonomous_engineer"
    if any(k in t for k in ["chaos", "resilience engineer", "chaos engineering", "sre specialist"]):
        return "site_reliability_engineer"
    if any(k in t for k in ["analyst", "business intelligence", "tableau", "power bi", "bi analyst"]):
        return "data_analyst"
    if any(k in t for k in ["qa", "sdet", "test automation", "tester", "quality engineer"]):
        return "qa_automation_engineer"
    if any(k in t for k in ["mobile", "ios", "android", "swift", "kotlin", "flutter", "react native"]):
        return "mobile_engineer"
    if any(k in t for k in ["fullstack", "full stack", "full-stack", "mern", "mean"]):
        return "fullstack_engineer"
    if any(k in t for k in ["data engineer", "etl", "data warehouse", "pipeline"]):
        return "data_engineer"
    if any(k in t for k in ["frontend", "front end", "react", "ui", "web engineer", "angular", "vue"]):
        return "frontend_engineer"
    if any(k in t for k in ["machine learning", "ml engineer", "deep learning", "ai engineer"]):
        return "ml_engineer"
    if any(k in t for k in ["devops", "sre", "site reliability", "cloud engineer", "infra"]):
        return "devops_sre"

    # Skills-based inference if title is generic
    if any(k in s for k in ["solidity", "web3", "smart contracts"]): return "blockchain_engineer"
    if any(k in s for k in ["c++", "rtos", "embedded", "i2c", "spi"]): return "embedded_iot_engineer"
    if any(k in s for k in ["llm", "rag", "langchain", "embeddings"]): return "nlp_engineer"
    if any(k in s for k in ["opencv", "yolo", "torchvision"]): return "computer_vision_engineer"
    if any(k in s for k in ["postgres", "mysql", "indexing", "wal"]): return "database_administrator"
    if any(k in s for k in ["terraform", "aws", "gcp", "architecture"]): return "cloud_architect"
    if any(k in s for k in ["argocd", "helm", "gitops"]): return "platform_engineer"
    if any(k in s for k in ["a/b testing", "statistics", "scikit-learn"]): return "data_scientist"
    if any(k in s for k in ["oauth2", "webhooks", "rest"]): return "api_integrations_engineer"
    if any(k in s for k in ["unity", "unreal", "opengl"]): return "game_developer"
    if any(k in s for k in ["siem", "wireshark", "splunk"]): return "cybersecurity_analyst"
    if any(k in s for k in ["owasp", "cryptography", "appsec"]): return "security_engineer"
    if any(k in s for k in ["bgp", "ospf", "tcp/ip", "cisco"]): return "network_engineer"
    if any(k in s for k in ["triton", "kubeflow", "model drift"]): return "aiops_mlops_engineer"
    if any(k in s for k in ["iceberg", "delta lake", "salting"]): return "big_data_architect"
    if any(k in s for k in ["salesforce", "apex", "soql"]): return "crm_enterprise_developer"
    if any(k in s for k in ["webxr", "quaternion", "spatial audio"]): return "ar_vr_engineer"
    if any(k in s for k in ["fix protocol", "vwap", "order matching"]): return "fintech_quant_developer"
    if any(k in s for k in ["fastq", "vcf", "biopython"]): return "bioinformatics_engineer"
    if any(k in s for k in ["ros 2", "ros", "slam", "lidar"]): return "robotics_autonomous_engineer"
    if any(k in s for k in ["chaos engineering", "error budget"]): return "site_reliability_engineer"
    if any(k in s for k in ["tableau", "powerbi", "sql analytics"]): return "data_analyst"
    if any(k in s for k in ["selenium", "playwright", "cypress", "pytest"]): return "qa_automation_engineer"
    if any(k in s for k in ["swift", "kotlin", "flutter"]): return "mobile_engineer"
    if any(k in s for k in ["sql", "etl", "spark", "hadoop", "bigquery"]): return "data_engineer"
    if any(k in s for k in ["react", "css", "html", "vue", "javascript"]): return "frontend_engineer"
    if any(k in s for k in ["pytorch", "tensorflow", "keras"]): return "ml_engineer"
    if any(k in s for k in ["kubernetes", "docker", "ansible"]): return "devops_sre"
    if any(k in s for k in ["node", "express", "django", "fastapi"]) and any(k in s for k in ["react", "vue"]): return "fullstack_engineer"

    return "software_engineer"


def _get_preset_questions(
    job_title: str,
    skills: List[str],
    duration_minutes: int,
    role_track: Optional[str] = None
) -> List[AssessmentQuestion]:
    """Resolves questions for the requested or auto-detected exam track."""
    track_key = role_track or detect_exam_track(job_title, skills)
    if track_key == "campus_graduate_engineer":
        return list(CAMPUS_GRADUATE_TRACK["questions"])
    track = EXAM_TRACKS.get(track_key, EXAM_TRACKS["software_engineer"])
    return track["questions"]


def generate_technical_assessment(
    job_title: str,
    required_skills: List[str],
    duration_minutes: int = 30,
    role_track: Optional[str] = None
) -> AssessmentPackage:
    """Generates a customized technical assessment tailored to role track and JD."""
    track_key = role_track or detect_exam_track(job_title, required_skills)
    eff_duration = 70 if track_key == "campus_graduate_engineer" and duration_minutes == 30 else duration_minutes
    questions = _get_preset_questions(job_title, required_skills, eff_duration, track_key)
    return AssessmentPackage(
        job_title=job_title,
        duration_minutes=eff_duration,
        total_questions=len(questions),
        questions=questions
    )


def evaluate_assessment_submission(
    questions: List[Dict[str, Any]],
    answers: Dict[str, str],
    sandbox_results: Optional[Dict[str, Any]] = None
) -> AssessmentEvaluationResult:
    """Evaluates candidate answers against engineering topics, MCQs, and sandbox test pass rates."""
    total_score = 0
    strengths = []
    weaknesses = []

    if not answers:
        return AssessmentEvaluationResult(
            score=0,
            strengths=[],
            weaknesses=["Candidate submitted empty answers."],
            feedback="Assessment was submitted with no answers recorded."
        )

    points_per_question = 100.0 / max(1, len(questions))

    for q in questions:
        q_id = q.get("id")
        ans = str(answers.get(q_id, "")).strip()
        expected = q.get("expected_topics", [])
        q_type = q.get("type", "coding")

        # 1. Evaluate Multiple Choice Questions (MCQ)
        if q_type == "mcq" or q.get("options"):
            correct_idx = q.get("correct_option")
            options = q.get("options", [])
            is_correct = False
            if correct_idx is not None and 0 <= correct_idx < len(options):
                expected_opt = options[correct_idx]
                clean_ans = ans.lower()
                clean_exp = expected_opt.lower()

                # Matches by index (e.g. "2" or 2)
                if clean_ans == str(correct_idx):
                    is_correct = True
                # Matches by full option text
                elif clean_ans == clean_exp:
                    is_correct = True
                # Matches by option letter prefix (e.g. "c" or "c)")
                elif len(clean_ans) <= 2 and clean_ans == clean_exp[:2].strip().replace(")", ""):
                    is_correct = True
                # Substring match if candidate typed option body
                elif len(clean_ans) > 3 and (clean_ans in clean_exp or clean_exp in clean_ans):
                    is_correct = True

            if is_correct:
                total_score += points_per_question
                strengths.append(f"Correctly answered MCQ: '{q.get('title')}'.")
            else:
                weaknesses.append(f"Incorrect answer for MCQ: '{q.get('title')}'.")
            continue

        # 2. Check if we have sandbox test results for this question
        sb_for_q = (sandbox_results or {}).get(q_id) if sandbox_results else None
        if not sb_for_q and q.get("test_cases") and ans:
            try:
                from src.services.sandbox_service import SandboxService
                lang = "sql" if q.get("type") == "sql" or q.get("section") == "sql" else "python"
                run_res = SandboxService.execute_code(
                    language=lang,
                    code=ans,
                    test_cases=q.get("test_cases", [])
                )
                sb_for_q = run_res.model_dump()
            except Exception:
                pass

        if sb_for_q and sb_for_q.get("total_tests", 0) > 0:
            pass_ratio = sb_for_q.get("tests_passed", 0) / sb_for_q.get("total_tests", 1)
            q_score = int(points_per_question * pass_ratio)
            total_score += q_score
            if pass_ratio == 1.0:
                strengths.append(f"Passed all automated sandbox test cases for '{q.get('title')}'.")
            elif pass_ratio > 0:
                strengths.append(f"Passed {sb_for_q.get('tests_passed')}/{sb_for_q.get('total_tests')} test cases for '{q.get('title')}'.")
                weaknesses.append(f"Some test cases failed for '{q.get('title')}'.")
            else:
                weaknesses.append(f"Failed sandbox test cases for '{q.get('title')}'.")
            continue

        # Otherwise evaluate code/text topics
        if not ans or len(ans) < 20:
            weaknesses.append(f"Incomplete response for {q.get('title')}.")
            continue

        matched_topics = [t for t in expected if any(w.lower() in ans.lower() for w in t.split())]
        match_ratio = len(matched_topics) / max(1, len(expected))
        q_score = int(points_per_question * max(0.4, match_ratio))
        total_score += q_score

        if match_ratio >= 0.5:
            strengths.append(f"Demonstrated solid understanding of {q.get('title')}.")
        else:
            weaknesses.append(f"Could elaborate deeper on {q.get('title')} (e.g. {expected[0] if expected else 'concepts'}).")

    final_score = min(100, max(15, round(total_score)))
    feedback = (
        f"Candidate achieved {final_score}/100 across {len(questions)} technical challenges. "
        f"{'Demonstrated strong engineering problem-solving and code execution.' if final_score >= 75 else 'Moderate performance; check edge cases and error boundaries.'}"
    )

    return AssessmentEvaluationResult(
        score=final_score,
        strengths=strengths or ["Solid code submission and engineering approach."],
        weaknesses=weaknesses or ["Minor omissions in edge case handling."],
        feedback=feedback
    )


class AssessmentService:
    def __init__(self, db: AsyncSession, org_id: UUID):
        self.db = db
        self.org_id = org_id

    async def generate_assessment(
        self, candidate_id: UUID, job_id: Optional[UUID] = None, duration_minutes: int = 30
    ) -> CandidateAssessment:
        c_stmt = select(Candidate).where(Candidate.id == candidate_id, Candidate.organization_id == self.org_id)
        c_res = await self.db.execute(c_stmt)
        candidate = c_res.scalar_one_or_none()
        if not candidate:
            raise ValueError("Candidate not found.")

        job_skills = []
        if job_id:
            j_stmt = select(JobOpening).where(JobOpening.id == job_id, JobOpening.organization_id == self.org_id)
            j_res = await self.db.execute(j_stmt)
            job = j_res.scalar_one_or_none()
            if job and job.required_skills:
                job_skills = job.required_skills

        job_title = job.title if (job_id and job) else "Software Engineer"
        skills = list(set((candidate.tags or ["Python", "PostgreSQL", "Docker"]) + job_skills))
        pkg = generate_technical_assessment(job_title=job_title, required_skills=skills, duration_minutes=duration_minutes)

        token, otp, expires_at = ProctoringService.generate_invite_credentials()

        assessment = CandidateAssessment(
            organization_id=self.org_id,
            job_id=job_id,
            candidate_id=candidate_id,
            duration_minutes=duration_minutes,
            status="pending",
            questions_json=[q.model_dump() for q in pkg.questions],
            answers_json={},
            access_token=token,
            otp_code=otp,
            otp_expires_at=expires_at,
            strike_count=0,
            max_strikes=3,
            integrity_score=100,
            proctoring_logs=[],
            snapshots_json=[],
            sandbox_results={}
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment

    async def evaluate_submission(
        self, assessment_id: UUID, answers: Dict[str, str]
    ) -> CandidateAssessment:
        stmt = select(CandidateAssessment).where(
            CandidateAssessment.id == assessment_id,
            CandidateAssessment.organization_id == self.org_id
        )
        res = await self.db.execute(stmt)
        assessment = res.scalar_one_or_none()
        if not assessment:
            raise ValueError("Assessment not found.")

        # Immutability Check: Completed assessments cannot be re-submitted or altered
        if assessment.status == "completed":
            raise ValueError("Assessment has already been completed and cannot be re-submitted.")

        # Disqualified assessments cannot be evaluated
        if assessment.status == "integrity_disqualified":
            raise ValueError("Assessment has been auto-terminated due to proctoring violations and cannot be evaluated.")

        questions = assessment.questions_json or []
        eval_result = evaluate_assessment_submission(
            questions=questions,
            answers=answers,
            sandbox_results=assessment.sandbox_results
        )

        assessment.answers_json = answers
        assessment.score = eval_result.score
        assessment.strengths = eval_result.strengths
        assessment.weaknesses = eval_result.weaknesses
        assessment.feedback = eval_result.feedback
        assessment.status = "completed"
        assessment.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment
