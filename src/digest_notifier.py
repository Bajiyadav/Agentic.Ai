import json
import logging
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger(__name__)

class DigestNotifier:
    """Dispatches 8:30 AM morning recruiter briefings to Slack channels and WhatsApp webhooks."""

    @staticmethod
    def format_slack_blocks(summary: Dict[str, Any], dashboard_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Creates a rich Slack Block Kit notification payload."""
        total = summary.get("total_candidates", 0)
        shortlisted = summary.get("shortlisted_count", 0)
        review = summary.get("review_count", 0)
        rejected = summary.get("rejected_count", 0)
        candidates = summary.get("candidates", [])

        # Top 3 Shortlisted candidates
        top_candidates = [c for c in candidates if c.get("recommendation") == "SHORTLIST"][:3]
        top_text_lines = []
        for c in top_candidates:
            top_text_lines.append(
                f"• *{c.get('candidate_name')}* ({c.get('overall_score')}/100) — GitHub: <https://github.com/{c.get('github_username')}|@{c.get('github_username')}>"
            )
        top_text = "\n".join(top_text_lines) if top_text_lines else "None shortlisted in this batch."

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🌅 Morning Recruitment Briefing — Candidate Audit Complete",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Good morning Team!*\nOur AI agent audited *{total} incoming applications* overnight.\nHere is your verified technical candidate breakdown:"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*🟢 Shortlisted (Top):*\n`{shortlisted}` candidates"},
                    {"type": "mrkdwn", "text": f"*🟡 Needs Review:*\n`{review}` candidates"},
                    {"type": "mrkdwn", "text": f"*🔴 Auto-Rejected:*\n`{rejected}` candidates"},
                    {"type": "mrkdwn", "text": f"*⏱️ Processing Time:*\n`{summary.get('processing_time_seconds', 0)}s`"}
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⭐ Top Shortlisted Candidates (Ready for Interview):*\n{top_text}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📊 View Morning Leaderboard", "emoji": True},
                        "url": dashboard_url,
                        "style": "primary"
                    }
                ]
            }
        ]

        return {"text": f"Morning Recruitment Brief: {shortlisted} candidates shortlisted from {total} applications.", "blocks": blocks}

    @staticmethod
    def format_whatsapp_message(summary: Dict[str, Any], dashboard_url: str = "http://localhost:8000") -> str:
        """Creates a compact, emoji-rich WhatsApp message."""
        total = summary.get("total_candidates", 0)
        shortlisted = summary.get("shortlisted_count", 0)
        rejected = summary.get("rejected_count", 0)
        candidates = summary.get("candidates", [])
        top = [c for c in candidates if c.get("recommendation") == "SHORTLIST"][:2]

        top_lines = "\n".join([f"• {c.get('candidate_name')} ({c.get('overall_score')}/100)" for c in top]) or "None"

        return (
            f"🌅 *Morning Recruitment Brief — AuditAgent*\n\n"
            f"Overnight applications: *{total}*\n"
            f"✅ *Shortlisted:* {shortlisted} | ❌ *Rejected:* {rejected}\n\n"
            f"⭐ *Top Candidates:*\n{top_lines}\n\n"
            f"👉 Review Leaderboard: {dashboard_url}"
        )

    @classmethod
    async def send_slack_notification(cls, webhook_url: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches notification to a live Slack webhook URL or provides simulated delivery."""
        payload = cls.format_slack_blocks(summary)
        
        if not webhook_url or "hooks.slack.com" not in webhook_url:
            # Demonstration mode
            return {
                "delivered": True,
                "mode": "simulated",
                "channel": "#hiring-team",
                "payload": payload,
                "message": "[DEMO MODE] Slack block notification generated successfully."
            }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json=payload, timeout=8)
                return {
                    "delivered": resp.status_code == 200,
                    "status_code": resp.status_code,
                    "mode": "live",
                    "payload": payload
                }
        except Exception as e:
            logger.error(f"Slack webhook dispatch error: {e}")
            return {"delivered": False, "error": str(e), "payload": payload}

    @classmethod
    async def send_whatsapp_notification(cls, phone_or_webhook: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches or simulates WhatsApp message brief."""
        text = cls.format_whatsapp_message(summary)
        return {
            "delivered": True,
            "mode": "simulated",
            "recipient": phone_or_webhook or "+91 98765 43210",
            "message_text": text,
            "message": "[DEMO MODE] WhatsApp brief created and ready for dispatch."
        }
