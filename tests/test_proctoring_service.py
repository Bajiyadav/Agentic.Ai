import pytest
import uuid
from datetime import datetime, timezone, timedelta
from src.db.models import CandidateAssessment
from src.services.proctoring_service import ProctoringService, ProctorTelemetryPayload

def test_proctoring_credentials():
    token, otp, expires_at = ProctoringService.generate_invite_credentials()
    assert len(token) >= 24
    assert len(otp) == 6
    assert otp.isdigit()
    assert expires_at > datetime.now(timezone.utc)

    ass = CandidateAssessment(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        access_token=token,
        otp_code=otp,
        otp_expires_at=expires_at
    )

    assert ProctoringService.verify_credentials(ass, token) is True
    assert ProctoringService.verify_credentials(ass, otp) is True
    assert ProctoringService.verify_credentials(ass, "wrong_otp") is False

def test_copy_paste_violation_strike():
    ass = CandidateAssessment(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        strike_count=0,
        max_strikes=3,
        integrity_score=100,
        proctoring_logs=[]
    )

    payload = ProctorTelemetryPayload(
        event_type="copy_paste_attempt",
        details="Attempted copy action."
    )
    res = ProctoringService.evaluate_telemetry(ass, payload)

    assert res.strike_added is True
    assert res.strike_count == 1
    assert ass.strike_count == 1
    assert res.integrity_score == 75
    assert ass.integrity_score == 75
    assert res.is_disqualified is False
    assert len(ass.proctoring_logs) == 1

def test_tab_and_fullscreen_violations():
    ass = CandidateAssessment(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        strike_count=1,
        max_strikes=3,
        integrity_score=75,
        proctoring_logs=[]
    )

    # Tab blur
    payload_tab = ProctorTelemetryPayload(event_type="tab_blur")
    res1 = ProctoringService.evaluate_telemetry(ass, payload_tab)
    assert res1.strike_added is True
    assert res1.strike_count == 2
    assert res1.integrity_score == 50

    # Fullscreen exit
    payload_fs = ProctorTelemetryPayload(event_type="fullscreen_exit")
    res2 = ProctoringService.evaluate_telemetry(ass, payload_fs)
    assert res2.strike_added is True
    assert res2.strike_count == 3
    assert res2.integrity_score == 25
    assert res2.is_disqualified is False

def test_strike_four_auto_termination():
    ass = CandidateAssessment(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        strike_count=3,
        max_strikes=3,
        integrity_score=25,
        status="in_progress",
        proctoring_logs=[]
    )

    # 4th violation causes immediate auto-termination!
    payload_4th = ProctorTelemetryPayload(event_type="copy_paste_attempt")
    res = ProctoringService.evaluate_telemetry(ass, payload_4th)

    assert res.status == "auto_terminated"
    assert res.is_disqualified is True
    assert res.strike_count == 4
    assert res.integrity_score == 0
    assert ass.status == "integrity_disqualified"
    assert ass.score == 0
    assert "terminated" in (ass.disqualification_reason or "").lower()

def test_audio_level_monitoring():
    ass = CandidateAssessment(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        strike_count=0,
        max_strikes=3,
        integrity_score=100,
        proctoring_logs=[]
    )

    # High audio RMS spike
    payload = ProctorTelemetryPayload(
        audio_level_rms=0.85,
        event_type="periodic_heartbeat"
    )
    res = ProctoringService.evaluate_telemetry(ass, payload)
    assert res.strike_added is True
    assert res.violation_type == "voice_activity"
    assert ass.strike_count == 1
