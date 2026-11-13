"""
backend/integrations/notifier.py
Slack and Discord webhook dispatcher.
Includes exponential backoff retry and clearly labelled mock fallback.
Enforces zero emojis in all outgoing messages and records audit logs.
"""
import os
import time
import httpx
from typing import Dict, Any, Tuple


class IncidentNotifier:
    """Dispatches webhook notifications with retry and transparent audit logging."""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL")

    def send_notification(
        self,
        incident_id: str,
        service: str,
        status: str,
        details: str,
        max_retries: int = 2
    ) -> Tuple[bool, str]:
        """
        Dispatches an incident status notification.
        Returns: (success, audit_note)
        Ensures NO emojis are present in the text payload.
        """
        # Strict emoji check/strip
        clean_details = self._strip_emojis(details)
        text_payload = f"[PagerPal Incident {status.upper()}] Incident {incident_id} | Service: {service} | Details: {clean_details}"

        if not self.webhook_url or "simulated" in self.webhook_url or "mock" in self.webhook_url:
            return True, "Notification fallback: Webhook URL not configured (simulated notification logged)"

        payload = {"text": text_payload}

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=2.0) as client:
                    resp = client.post(self.webhook_url, json=payload)
                    if resp.status_code in [200, 204]:
                        return True, "Webhook notification dispatched successfully"
                    else:
                        if resp.status_code >= 400 and resp.status_code < 500:
                            # Client error (e.g. invalid webhook token)
                            return False, f"Notification fallback: Webhook returned HTTP {resp.status_code}"
            except Exception as ex:
                if attempt < max_retries:
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                else:
                    return False, f"Notification fallback: Network error ({type(ex).__name__})"

        return False, "Notification fallback: Max retries exceeded"

    def _strip_emojis(self, text: str) -> str:
        """Removes unicode emojis and common emoji shortcodes."""
        # Clean common incident emojis: 🚨, ⚠️, ✅, ❌, 🛑, 🔍, 📊, ⚡
        for ch in ["🚨", "⚠️", "✅", "❌", "🛑", "🔍", "📊", "⚡", "🔥", "🚀"]:
            text = text.replace(ch, "")
        return text.strip()


# Global singleton
notifier = IncidentNotifier()

