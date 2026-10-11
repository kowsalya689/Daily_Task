"""Telegram alerts for negative feedback (Phase 13 of the build guide, hardened).

Credentials come from environment variables / .env, never from source code.

CLI helpers:
    python -m src.alerts.telegram_alert chat-id   # find your chat id
    python -m src.alerts.telegram_alert test      # send a test message
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

log = logging.getLogger("alerts")
MAX_LEN = 4000  # Telegram's hard limit is 4096 characters


def _creds():
    return os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")


def telegram_configured() -> bool:
    token, chat_id = _creds()
    return bool(token and chat_id)


def send_negative_alert(text: str, confidence: Optional[float] = None,
                        contact: Optional[str] = None) -> bool:
    """Message the business owner. Returns True on success; never raises,
    so a Telegram outage cannot break the customer's submission."""
    token, chat_id = _creds()
    if not (token and chat_id):
        log.warning("Telegram not configured; negative feedback was not sent.")
        return False

    lines = ["NEGATIVE FEEDBACK"]
    if confidence is not None:
        lines.append(f"Model confidence: {confidence:.0%}")
    lines.append(f"Customer: {contact}" if contact else "Customer: not provided")
    lines += ["", text]
    message = "\n".join(lines)[:MAX_LEN]

    try:
        # Plain text (no parse_mode) so customer text can't break formatting.
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        # Don't log str(exc): requests includes the URL, which contains the token.
        status = getattr(getattr(exc, "response", None), "status_code", "no response")
        log.error("Telegram alert failed (%s: %s)", type(exc).__name__, status)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    token, _ = _creds()
    if cmd == "chat-id":
        if not token:
            sys.exit("Set TELEGRAM_BOT_TOKEN in .env first.")
        r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
        r.raise_for_status()
        chats = {u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name", "")
                 for u in r.json().get("result", []) if "message" in u}
        print(chats or "No messages yet - send any message to your bot, then run this again.")
    elif cmd == "test":
        ok = send_negative_alert("This is a test alert from the Feedback Analyser.", 0.99, "Test")
        print("Sent." if ok else "Failed - check the token and chat id in .env.")
    else:
        sys.exit(__doc__)
