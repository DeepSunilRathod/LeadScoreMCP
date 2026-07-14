"""
lib/leads.py — Lead scoring & CRM analytics
Matches original JS dashboard logic exactly: scores EVERY call row individually
(no deduplication by lead_id) — mirrors "Total Leads = all call records".
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import query


def calculate_score(call):
    """
    Score a single call based on duration, status, recording availability, and call type.
    Mirrors the original JS calculateScore() logic exactly.
    """
    score = 0

    duration = call.get("call_duration_sec") or 0

    if duration > 300:
        score += 40
    elif duration > 120:
        score += 25
    elif duration > 30:
        score += 10

    status_lower = (call.get("status") or "").strip().lower()
    if "answer" in status_lower or "completed" in status_lower:
        score += 30

    rec_url = (call.get("recording_url") or "").strip()
    if rec_url and rec_url.upper() != "NULL" and rec_url != "":
        score += 10

    ct_lower = (call.get("call_type") or "").strip().lower()
    if ct_lower in ("incoming", "inbound"):
        score += 20

    return score


def get_lead_category(score):
    if score > 20:
        return "Hot"
    if score > 10:
        return "Warm"
    return "Cold"


def _compute_all_lead_scores():
    """
    Score EVERY call row as its own 'lead' entry — matches original dashboard.
    No grouping/deduplication by lead_id.
    """
    calls = query("SELECT * FROM calls WHERE source = 'primary'")

    results = []
    for c in calls:
        score = calculate_score(c)
        results.append({
            "lead_id": c["lead_id"],
            "call_id": c["id"],
            "agent_name": c["agent_name"],
            "phone_number": c["phone_number"],
            "status": c["status"],
            "call_type": c["call_type"],
            "call_duration_sec": c["call_duration_sec"],
            "recording_url": c["recording_url"],
            "call_date": str(c["call_date"]) if c["call_date"] else None,
            "transcript_status": c["transcript_status"],
            "score": score,
            "category": get_lead_category(score),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_all_leads(limit=50):
    return _compute_all_lead_scores()[:limit]


def get_hot_leads(limit=20):
    all_leads = _compute_all_lead_scores()
    hot = [l for l in all_leads if l["category"] == "Hot"]
    return hot[:limit]


def get_warm_leads(limit=20):
    all_leads = _compute_all_lead_scores()
    warm = [l for l in all_leads if l["category"] == "Warm"]
    return warm[:limit]


def get_cold_leads(limit=20):
    all_leads = _compute_all_lead_scores()
    cold = [l for l in all_leads if l["category"] == "Cold"]
    return cold[:limit]


def get_top_10_leads():
    return _compute_all_lead_scores()[:10]


def get_lead_detail(lead_id):
    """Return ALL call rows for this lead_id (since a lead can have multiple calls)."""
    lead_id = str(lead_id)
    calls = query(
        "SELECT * FROM calls WHERE lead_id = %s ORDER BY call_date DESC",
        [lead_id],
    )

    if not calls:
        return None

    call_entries = []
    for c in calls:
        score = calculate_score(c)
        call_entries.append({
            "call_id": c["id"],
            "status": c["status"],
            "call_type": c["call_type"],
            "duration_sec": c["call_duration_sec"],
            "call_date": str(c["call_date"]) if c["call_date"] else None,
            "has_transcript": c["transcript_status"] == "done",
            "score": score,
            "category": get_lead_category(score),
        })

    best = max(call_entries, key=lambda x: x["score"])

    return {
        "lead_id": lead_id,
        "agent_name": calls[0]["agent_name"],
        "total_calls": len(calls),
        "best_score": best["score"],
        "best_category": best["category"],
        "call_history": call_entries,
    }


def get_dashboard_stats():
    """Overall stats — Total Leads = total call rows (matches original dashboard)."""
    all_leads = _compute_all_lead_scores()
    transcribed = query("SELECT COUNT(*) as c FROM calls WHERE transcript_status = 'done'")[0]["c"]  # counts ALL sources

    hot = sum(1 for l in all_leads if l["category"] == "Hot")
    warm = sum(1 for l in all_leads if l["category"] == "Warm")
    cold = sum(1 for l in all_leads if l["category"] == "Cold")

    return {
        "total_leads": len(all_leads),
        "transcribed_calls": transcribed,
        "hot_leads": hot,
        "warm_leads": warm,
        "cold_leads": cold,
        "avg_score": round(sum(l["score"] for l in all_leads) / len(all_leads), 1) if all_leads else 0,
    }


def get_agent_performance(agent_name):
    calls = query(
        "SELECT * FROM calls WHERE agent_name LIKE %s",
        [f"%{agent_name}%"],
    )

    if not calls:
        return None

    total = len(calls)
    completed = sum(1 for c in calls if "answer" in (c["status"] or "").lower() or "completed" in (c["status"] or "").lower())
    transcribed = sum(1 for c in calls if c["transcript_status"] == "done")

    scores = [calculate_score(c) for c in calls]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    hot_count = sum(1 for s in scores if get_lead_category(s) == "Hot")

    return {
        "agent_name": agent_name,
        "total_calls": total,
        "completed_calls": completed,
        "connect_rate": round(completed / total, 2) if total else 0,
        "transcribed_calls": transcribed,
        "avg_score": avg_score,
        "hot_leads_generated": hot_count,
    }


def get_call_analytics():
    calls = query("SELECT status, call_duration_sec, transcript_status, call_type FROM calls")

    total = len(calls)
    status_breakdown = {}
    type_breakdown = {}
    for c in calls:
        s = c["status"] or "Unknown"
        status_breakdown[s] = status_breakdown.get(s, 0) + 1
        t = c["call_type"] or "Unknown"
        type_breakdown[t] = type_breakdown.get(t, 0) + 1

    scores = [calculate_score(c) for c in calls]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    transcribed = sum(1 for c in calls if c["transcript_status"] == "done")

    return {
        "total_calls": total,
        "status_breakdown": status_breakdown,
        "call_type_breakdown": type_breakdown,
        "avg_score": avg_score,
        "transcribed_calls": transcribed,
        "transcription_rate": round(transcribed / total * 100, 1) if total else 0,
    }


def recommend_leads(count=5):
    all_leads = _compute_all_lead_scores()
    candidates = [l for l in all_leads if l["category"] in ("Hot", "Warm")]
    return candidates[:count]

def add_lead_note(lead_id, note_text):
    """Add a note to a lead."""
    from lib.db import execute
    execute(
        "INSERT INTO lead_notes (lead_id, note) VALUES (%s, %s)",
        [str(lead_id), note_text],
    )
    return True


def get_lead_notes(lead_id):
    """Get all notes for a lead, newest first."""
    rows = query(
        "SELECT id, note, created_at FROM lead_notes WHERE lead_id = %s ORDER BY created_at DESC",
        [str(lead_id)],
    )
    return rows


def search_leads_and_calls(search_term):
    """
    Global search: matches lead_id, call_id, agent_name, or phone_number.
    Returns matching calls (each row = a call, which links to a lead).
    """
    term = f"%{search_term}%"
    rows = query(
        """
        SELECT id as call_id, lead_id, agent_name, phone_number, status, call_date
        FROM calls
        WHERE lead_id LIKE %s OR id LIKE %s OR agent_name LIKE %s OR phone_number LIKE %s
        LIMIT 30
        """,
        [term, term, term, term],
    )
    return rows

def find_duplicate_phone_numbers():
    """
    Find phone numbers that appear under multiple different lead_ids —
    likely the same person entered as separate leads.
    """
    rows = query(
        """
        SELECT phone_number, COUNT(DISTINCT lead_id) as lead_count,
               GROUP_CONCAT(DISTINCT lead_id) as lead_ids
        FROM calls
        WHERE phone_number IS NOT NULL AND phone_number != ''
        GROUP BY phone_number
        HAVING lead_count > 1
        ORDER BY lead_count DESC
        LIMIT 50
        """
    )
    return rows

if __name__ == "__main__":
    print("Testing lead scoring (matches reference dashboard)...\n")

    stats = get_dashboard_stats()
    print("Dashboard Stats:", stats)

    print("\nTop 10 Leads:")
    for l in get_top_10_leads():
        print(f"  Call {l['call_id']} (Lead {l['lead_id']}): Score={l['score']} ({l['category']}) - {l['agent_name']}")