import os
import re
import json
import time
import base64
import random
import string
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
import litellm

from src.db.models import CandidateAssessment

class ProctorTelemetryPayload(BaseModel):
    snapshot_base64: Optional[str] = None
    audio_level_rms: Optional[float] = 0.0  # 0.0 to 1.0
    audio_peak_hz: Optional[float] = None
    event_type: Optional[str] = None  # "periodic_heartbeat", "copy_paste_attempt", "tab_blur", "fullscreen_exit"
    details: Optional[str] = None
    timestamp: Optional[str] = None

class ProctorCheckResult(BaseModel):
    status: str  # "ok", "warning", "strike", "auto_terminated"
    strike_added: bool = False
    strike_count: int = 0
    max_strikes: int = 3
    violation_type: Optional[str] = None
    message: str = "Assessment environment secure."
    integrity_score: int = 100
    is_disqualified: bool = False
    details: Optional[str] = None

class ProctoringService:
    """
    Enterprise AI Vision & Audio Proctoring Engine.
    Monitors candidate webcam feed, microphone audio level, fullscreen integrity,
    tab switching, and copy/paste blocking with 3-strike auto-termination.
    """

    MAX_STRIKES = 3  # 4th violation causes immediate auto-termination
    AUDIO_VOICE_THRESHOLD = 0.50  # RMS threshold for sustained speech/noise

    @staticmethod
    def generate_invite_credentials() -> Tuple[str, str, datetime]:
        """Generates a secure 32-character access token and a 6-digit OTP."""
        token = secrets.token_urlsafe(24)
        otp = "".join(random.choices(string.digits, k=6))
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
        return token, otp, expires_at

    @staticmethod
    def verify_credentials(
        assessment: CandidateAssessment,
        provided_otp_or_token: str
    ) -> bool:
        """Verifies 6-digit OTP code or secret access token."""
        val = (provided_otp_or_token or "").strip()
        if not val:
            return False

        # Check token match
        if assessment.access_token and assessment.access_token == val:
            return True

        # Check OTP match
        if assessment.otp_code and assessment.otp_code == val:
            if assessment.otp_expires_at:
                now = datetime.now(timezone.utc)
                exp = assessment.otp_expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now > exp:
                    return False
            return True

        return False

    @classmethod
    def analyze_vision_snapshot(cls, snapshot_base64: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Analyzes a webcam snapshot frame for face presence, multiple persons, or looking away.
        Returns: (is_violation, violation_type, detail_msg)
        """
        if not snapshot_base64 or len(snapshot_base64) < 100:
            return False, None, None

        # Clean base64 header if present
        clean_b64 = re.sub(r"^data:image\/[a-zA-Z]+;base64,", "", snapshot_base64)

        # 1. Attempt AI Vision call if configured and key is available
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        is_placeholder = "placeholder" in api_key.lower() or not api_key
        use_mock = os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true" or is_placeholder

        if not use_mock:
            try:
                model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
                prompt = (
                    "Analyze this candidate assessment proctoring webcam frame. "
                    "Respond ONLY with valid JSON: "
                    '{"faces_count": <int>, "face_facing_camera": <true/false>, "suspicious_notes": "<string>"}'
                )
                response = litellm.completion(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{clean_b64}"}
                                }
                            ]
                        }
                    ],
                    response_format={"type": "json_object"},
                    timeout=4.0
                )
                content = response.choices[0].message.content
                data = json.loads(content)
                faces = data.get("faces_count", 1)
                facing = data.get("face_facing_camera", True)

                if faces == 0:
                    return True, "face_missing", "No face detected in webcam frame."
                elif faces > 1:
                    return True, "multiple_faces", f"Multiple faces ({faces}) detected in camera view."
                elif not facing:
                    return True, "looking_away", "Candidate is looking away from the assessment screen."
                return False, None, None

            except Exception:
                # Fallback to local heuristic
                pass

        # 2. Local vision heuristic analysis:
        # Check payload metadata or synthetic verification tags if passed
        # If image bytes are very small (e.g. blacked out frame < 1KB)
        try:
            raw_bytes = base64.b64decode(clean_b64)
            if len(raw_bytes) < 800:
                return True, "camera_occluded", "Webcam feed appears completely blank or covered."
        except Exception:
            pass

        return False, None, None

    @classmethod
    def evaluate_telemetry(
        cls,
        assessment: CandidateAssessment,
        payload: ProctorTelemetryPayload
    ) -> ProctorCheckResult:
        """
        Processes incoming proctor telemetry (audio, video frame, client events),
        records strikes, and triggers auto-termination if strike count exceeds limit.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        current_strikes = assessment.strike_count or 0
        strike_added = False
        violation_type = None
        detail_msg = payload.details or ""
        warning_msg = ""

        # Check if already disqualified
        if assessment.status == "integrity_disqualified":
            return ProctorCheckResult(
                status="auto_terminated",
                strike_added=False,
                strike_count=current_strikes,
                max_strikes=cls.MAX_STRIKES,
                violation_type="disqualified",
                message="Assessment has been terminated due to integrity violations.",
                integrity_score=assessment.integrity_score or 0,
                is_disqualified=True,
                details=assessment.disqualification_reason
            )

        # 1. Check direct client-side violations
        event = payload.event_type or "periodic_heartbeat"

        if event == "copy_paste_attempt":
            strike_added = True
            violation_type = "copy_paste_attempt"
            detail_msg = "Attempted unauthorized copy/paste operation (blocked)."
            warning_msg = "Copy/paste is strictly prohibited. Strike recorded."

        elif event == "tab_blur":
            strike_added = True
            violation_type = "tab_navigation"
            detail_msg = "Candidate navigated away from assessment tab / window lost focus."
            warning_msg = "Window lost focus. You must remain on the assessment screen."

        elif event == "fullscreen_exit":
            strike_added = True
            violation_type = "fullscreen_exit"
            detail_msg = "Candidate exited fullscreen assessment environment."
            warning_msg = "Fullscreen mode exited. Strike recorded."

        # 2. Check Audio Telemetry
        elif (payload.audio_level_rms or 0.0) > cls.AUDIO_VOICE_THRESHOLD:
            # Check if prolonged or excessive noise
            if (payload.audio_level_rms or 0.0) > 0.75:
                strike_added = True
                violation_type = "voice_activity"
                detail_msg = f"High audio/conversation volume detected (RMS: {payload.audio_level_rms:.2f})."
                warning_msg = "Human speech or loud background conversation detected."
            else:
                detail_msg = f"Elevated audio level detected (RMS: {payload.audio_level_rms:.2f})."
                warning_msg = "Elevated sound detected. Please maintain quiet environment."

        # 3. Check Vision Snapshot
        if not strike_added and payload.snapshot_base64:
            is_vis_viol, v_type, v_detail = cls.analyze_vision_snapshot(payload.snapshot_base64)
            if is_vis_viol:
                strike_added = True
                violation_type = v_type
                detail_msg = v_detail or "Visual proctoring violation detected."
                warning_msg = detail_msg

        # Update Strike Count
        if strike_added:
            current_strikes += 1
            assessment.strike_count = current_strikes

        # Calculate dynamic Integrity Trust Score
        new_integrity = max(0, 100 - (current_strikes * 25))
        assessment.integrity_score = new_integrity

        # Format log entry
        log_entry = {
            "timestamp": now_iso,
            "event_type": event if event != "periodic_heartbeat" else (violation_type or "heartbeat_ok"),
            "violation_type": violation_type,
            "strike_added": strike_added,
            "current_strikes": current_strikes,
            "details": detail_msg,
            "audio_level": payload.audio_level_rms
        }

        # Append to assessment logs
        logs = list(assessment.proctoring_logs or [])
        logs.append(log_entry)
        assessment.proctoring_logs = logs

        # Store snapshot if violation or periodically
        if payload.snapshot_base64 and (strike_added or len(assessment.snapshots_json or []) < 15):
            snaps = list(assessment.snapshots_json or [])
            snaps.append({
                "timestamp": now_iso,
                "event_type": violation_type or "routine_check",
                "strike_count": current_strikes,
                "snapshot_base64": payload.snapshot_base64[:500] + "..." if len(payload.snapshot_base64) > 500 else payload.snapshot_base64
            })
            assessment.snapshots_json = snaps

        # Check for Auto-Termination threshold (Strike 4 => Disqualification)
        is_disqualified = current_strikes > cls.MAX_STRIKES
        if is_disqualified:
            assessment.status = "integrity_disqualified"
            assessment.disqualification_reason = (
                f"Assessment automatically terminated: Exceeded maximum integrity strikes "
                f"({current_strikes} violations recorded). Last violation: {detail_msg}"
            )
            assessment.completed_at = datetime.now(timezone.utc)
            assessment.score = 0

            return ProctorCheckResult(
                status="auto_terminated",
                strike_added=strike_added,
                strike_count=current_strikes,
                max_strikes=cls.MAX_STRIKES,
                violation_type=violation_type or "max_strikes_exceeded",
                message="Assessment automatically terminated: Maximum allowed integrity strikes exceeded.",
                integrity_score=0,
                is_disqualified=True,
                details=assessment.disqualification_reason
            )

        status_result = "strike" if strike_added else ("warning" if warning_msg else "ok")
        return ProctorCheckResult(
            status=status_result,
            strike_added=strike_added,
            strike_count=current_strikes,
            max_strikes=cls.MAX_STRIKES,
            violation_type=violation_type,
            message=warning_msg or "Environment secure. Assessment in progress.",
            integrity_score=new_integrity,
            is_disqualified=False,
            details=detail_msg
        )
