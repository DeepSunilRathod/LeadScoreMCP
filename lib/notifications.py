"""
lib/notifications.py — Email (Gmail SMTP) and WhatsApp (Twilio) sending
with message history logging and multi-language template support.
"""

import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    GMAIL_ADDRESS, GMAIL_APP_PASSWORD,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
)
from lib.db import query, execute
from lib.logger import log_error, log_info


# ============================================================
# TEMPLATES (Multi-language)
# ============================================================

WHATSAPP_TEMPLATES = {
    "en": "Hi {name}! 👋 Just following up on our recent conversation. I'd love to help answer any questions and discuss next steps. Let me know a good time to connect!",
    "hi": "नमस्ते {name}! 👋 हमारी हाल की बातचीत को लेकर फॉलो-अप कर रहा हूँ। मैं आपके किसी भी सवाल का जवाब देने और अगले कदमों पर चर्चा करने में मदद करना चाहूँगा। बताइए कब बात करना सही रहेगा!",
}

EMAIL_TEMPLATES = {
    "en": {
        "subject": "Following up on our conversation",
        "body": """Hi {name},

I wanted to follow up on our recent conversation. I'd love to answer 
any questions you might have and discuss next steps.

Please let me know a good time to connect, or feel free to reply 
directly to this email.

Looking forward to hearing from you!

Best regards,
Sales Team
(Lead ID: {lead_id})
""",
    },
    "hi": {
        "subject": "हमारी बातचीत को लेकर फॉलो-अप",
        "body": """नमस्ते {name},

मैं हमारी हाल की बातचीत को लेकर फॉलो-अप करना चाहता था। मैं आपके किसी 
भी सवाल का जवाब देने और अगले कदमों पर चर्चा करने में खुशी होगी।

कृपया मुझे बताएं कि बात करने का सही समय क्या रहेगा, या इस ईमेल का 
सीधे जवाब दें।

आपसे सुनने के लिए उत्सुक हूं!

सादर,
सेल्स टीम
(Lead ID: {lead_id})
""",
    },
}


# ============================================================
# LOGGING HELPER
# ============================================================

def _log_message(lead_id, call_id, channel, recipient, message, status):
    try:
        execute(
            """
            INSERT INTO message_log (lead_id, call_id, channel, recipient, message, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [lead_id, call_id, channel, recipient, message, status],
        )
    except Exception as e:
        log_error(f"Failed to log message: {e}")


def was_contacted_recently(lead_id, channel=None, within_days=3):
    """Check if a lead was already contacted within the last N days."""
    sql = """
        SELECT COUNT(*) as c FROM message_log
        WHERE lead_id = %s AND status = 'sent'
        AND sent_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
    """
    params = [str(lead_id), within_days]
    if channel:
        sql += " AND channel = %s"
        params.append(channel)

    rows = query(sql, params)
    return rows[0]["c"] > 0 if rows else False


# ============================================================
# EMAIL (Gmail SMTP)
# ============================================================

def send_email(to_address, subject, body, lead_id=None):
    """Send a plain-text email via Gmail SMTP. Logs the attempt."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return False, "Gmail credentials not configured in .env"

    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        if lead_id:
            _log_message(lead_id, None, "email", to_address, body, "sent")
        log_info(f"Email sent to {to_address}")
        return True, f"Email sent to {to_address}"
    except Exception as e:
        if lead_id:
            _log_message(lead_id, None, "email", to_address, body, "failed")
        log_error(f"Email send failed to {to_address}: {e}")
        return False, f"Failed to send email: {str(e)}"


def send_followup_email(lead_id, to_address, lead_name=None, language="en"):
    """Send a templated follow-up email for a specific lead."""
    name = lead_name or "there"
    tpl = EMAIL_TEMPLATES.get(language, EMAIL_TEMPLATES["en"])
    subject = tpl["subject"]
    body = tpl["body"].format(name=name, lead_id=lead_id)
    return send_email(to_address, subject, body, lead_id=lead_id)


# ============================================================
# WHATSAPP (Twilio Sandbox)
# ============================================================

def send_whatsapp(to_phone, message, lead_id=None):
    """Send a WhatsApp message via Twilio sandbox. Logs the attempt."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False, "Twilio credentials not configured in .env"

    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        formatted_to = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"

        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=message,
            to=formatted_to,
        )

        if lead_id:
            _log_message(lead_id, None, "whatsapp", to_phone, message, "sent")
        log_info(f"WhatsApp sent to {to_phone} (SID: {msg.sid})")
        return True, f"WhatsApp sent (SID: {msg.sid})"
    except Exception as e:
        if lead_id:
            _log_message(lead_id, None, "whatsapp", to_phone, message, "failed")
        log_error(f"WhatsApp send failed to {to_phone}: {e}")
        return False, f"Failed to send WhatsApp: {str(e)}"


def send_followup_whatsapp(lead_id, to_phone, lead_name=None, language="en"):
    """Send a templated follow-up WhatsApp message for a specific lead."""
    name = lead_name or "there"
    template = WHATSAPP_TEMPLATES.get(language, WHATSAPP_TEMPLATES["en"])
    message = template.format(name=name)
    return send_whatsapp(to_phone, message, lead_id=lead_id)


def format_phone_for_whatsapp(raw_phone):
    """Convert a raw phone number into E.164 format with + prefix."""
    if not raw_phone:
        return None

    digits = "".join(c for c in str(raw_phone) if c.isdigit())
    if not digits:
        return None

    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    elif len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) > 10:
        return f"+{digits}"

    return None


def send_whatsapp_followup_by_lead(lead_id, language="en", skip_if_recent=True):
    """
    Look up a lead's phone number and send a WhatsApp follow-up.
    Skips sending if already contacted within 3 days (unless skip_if_recent=False).
    """
    if skip_if_recent and was_contacted_recently(lead_id, channel="whatsapp", within_days=3):
        return False, f"Lead {lead_id} was already contacted via WhatsApp within the last 3 days — skipped"

    rows = query(
        "SELECT DISTINCT lead_id, phone_number, agent_name FROM calls WHERE lead_id = %s AND phone_number IS NOT NULL LIMIT 1",
        [str(lead_id)],
    )

    if not rows:
        return False, f"No phone number found for lead {lead_id}"

    raw_phone = rows[0]["phone_number"]
    formatted = format_phone_for_whatsapp(raw_phone)

    if not formatted:
        return False, f"Could not format phone number '{raw_phone}' for lead {lead_id}"

    success, msg = send_followup_whatsapp(lead_id, formatted, language=language)
    return success, f"{msg} (sent to {formatted})"


# ============================================================
# BULK SEND CAMPAIGNS
# ============================================================

def bulk_send_whatsapp_to_category(category="Hot", limit=20, language="en", skip_if_recent=True):
    """
    Send WhatsApp follow-ups to all leads in a category (Hot/Warm/Cold).
    Returns a summary of results.
    """
    from lib.leads import get_hot_leads, get_warm_leads, get_cold_leads

    if category == "Hot":
        leads = get_hot_leads(limit)
    elif category == "Warm":
        leads = get_warm_leads(limit)
    else:
        leads = get_cold_leads(limit)

    results = {"sent": 0, "skipped": 0, "failed": 0, "details": []}

    seen_leads = set()
    for lead in leads:
        lid = lead["lead_id"]
        if lid in seen_leads:
            continue
        seen_leads.add(lid)

        success, msg = send_whatsapp_followup_by_lead(lid, language=language, skip_if_recent=skip_if_recent)

        if success:
            results["sent"] += 1
        elif "already contacted" in msg:
            results["skipped"] += 1
        else:
            results["failed"] += 1

        results["details"].append({"lead_id": lid, "success": success, "message": msg})

    return results


# Quick self-test
if __name__ == "__main__":
    print("Notification module loaded.")
    print(f"Gmail configured: {bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)}")
    print(f"Twilio configured: {bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)}")