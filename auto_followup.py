"""
auto_followup.py — Automatically send WhatsApp follow-ups to high-readiness
leads that haven't been contacted recently.

Rule: readiness_score >= 60 AND not contacted via WhatsApp in the last 3 days.

Run manually:
    py auto_followup.py

Or schedule via Windows Task Scheduler to run daily.
"""

from lib.db import query
from lib.notifications import send_whatsapp_followup_by_lead
from lib.logger import log_info, log_error

READINESS_THRESHOLD = 60
LIMIT = 20


def get_auto_followup_candidates():
    """Get leads matching the auto-follow-up rule."""
    rows = query(
        """
        SELECT DISTINCT isa.lead_id, isa.readiness_score, isa.buyer_intent
        FROM intent_sentiment_analyses isa
        WHERE isa.readiness_score >= %s
        ORDER BY isa.readiness_score DESC
        LIMIT %s
        """,
        [READINESS_THRESHOLD, LIMIT],
    )
    return rows


def run_auto_followup():
    candidates = get_auto_followup_candidates()
    log_info(f"Auto-followup: found {len(candidates)} candidates (readiness >= {READINESS_THRESHOLD})")

    sent = 0
    skipped = 0
    failed = 0

    for c in candidates:
        lead_id = c["lead_id"]
        success, msg = send_whatsapp_followup_by_lead(lead_id, skip_if_recent=True)

        if success:
            sent += 1
            print(f"  SENT to lead {lead_id}: {msg}")
        elif "already contacted" in msg:
            skipped += 1
            print(f"  SKIPPED lead {lead_id}: {msg}")
        else:
            failed += 1
            print(f"  FAILED lead {lead_id}: {msg}")

    summary = f"Auto-followup complete: {sent} sent, {skipped} skipped, {failed} failed"
    print(f"\n{summary}")
    log_info(summary)


if __name__ == "__main__":
    run_auto_followup()