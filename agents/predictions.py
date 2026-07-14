"""
agents/predictions.py — AI Sales Prediction, Revenue Forecasting,
Next Best Action, and Site Visit Probability
Built on top of saved call_analyses + intent_sentiment_analyses data.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import query


def _get_lead_signals(lead_id=None):
    """
    Pull combined signals (quality + intent) per lead for scoring.
    If lead_id is None, returns ALL leads with data.
    """
    sql = """
        SELECT
            c.lead_id, c.id as call_id, c.agent_name, c.call_date,
            ca.quality_score, ca.call_outcome,
            isa.buyer_intent, isa.readiness_score, isa.engagement_level,
            isa.final_sentiment
        FROM calls c
        LEFT JOIN call_analyses ca ON c.id = ca.call_id
        LEFT JOIN intent_sentiment_analyses isa ON c.id = isa.call_id
        WHERE (ca.call_id IS NOT NULL OR isa.call_id IS NOT NULL)
    """
    params = []
    if lead_id:
        sql += " AND c.lead_id = %s"
        params.append(str(lead_id))

    return query(sql, params)


# ============================================================
# 1. SALES PREDICTION
# ============================================================

INTENT_WEIGHTS = {
    "ready_to_buy": 90,
    "actively_considering": 65,
    "researching": 35,
    "skeptical": 15,
    "not_interested": 2,
}

SENTIMENT_WEIGHTS = {
    "very_positive": 15,
    "positive": 10,
    "neutral": 0,
    "negative": -10,
    "very_negative": -15,
}

ENGAGEMENT_WEIGHTS = {
    "high": 15,
    "medium": 5,
    "low": -10,
}


def calculate_conversion_probability(row):
    """
    Combine quality_score, readiness_score, intent, sentiment, engagement
    into a single 0-100 conversion probability.
    """
    score = 0
    weight_sum = 0

    if row.get("quality_score") is not None:
        score += row["quality_score"] * 0.3
        weight_sum += 0.3

    if row.get("readiness_score") is not None:
        score += row["readiness_score"] * 0.4
        weight_sum += 0.4

    intent_score = INTENT_WEIGHTS.get(row.get("buyer_intent"), 20)
    score += intent_score * 0.3
    weight_sum += 0.3

    base = score / weight_sum if weight_sum else 0

    # Adjustments
    base += SENTIMENT_WEIGHTS.get(row.get("final_sentiment"), 0) * 0.3
    base += ENGAGEMENT_WEIGHTS.get(row.get("engagement_level"), 0) * 0.3

    return max(0, min(100, round(base)))


def get_sales_predictions(limit=15):
    """Get leads ranked by predicted conversion probability."""
    rows = _get_lead_signals()

    results = []
    for r in rows:
        prob = calculate_conversion_probability(r)
        results.append({
            "lead_id": r["lead_id"],
            "call_id": r["call_id"],
            "agent_name": r["agent_name"],
            "conversion_probability": prob,
            "buyer_intent": r["buyer_intent"],
            "quality_score": r["quality_score"],
        })

    results.sort(key=lambda x: x["conversion_probability"], reverse=True)
    return results[:limit]


def get_lead_prediction(lead_id):
    """Get conversion probability for one specific lead."""
    rows = _get_lead_signals(lead_id)
    if not rows:
        return None

    # Use the most recent/best call for this lead
    best_row = max(rows, key=lambda r: calculate_conversion_probability(r))
    prob = calculate_conversion_probability(best_row)

    return {
        "lead_id": lead_id,
        "conversion_probability": prob,
        "buyer_intent": best_row.get("buyer_intent"),
        "quality_score": best_row.get("quality_score"),
        "readiness_score": best_row.get("readiness_score"),
        "sentiment": best_row.get("final_sentiment"),
        "engagement": best_row.get("engagement_level"),
    }


# ============================================================
# 2. REVENUE FORECASTING (Conversion Count Based — No $ Value)
# ============================================================

def get_conversion_forecast():
    """
    Forecast expected number of conversions based on probability buckets.
    No dollar amount since business has no fixed deal value.
    """
    rows = _get_lead_signals()

    buckets = {"very_likely": 0, "likely": 0, "possible": 0, "unlikely": 0}
    expected_conversions = 0.0

    for r in rows:
        prob = calculate_conversion_probability(r)
        expected_conversions += prob / 100

        if prob >= 75:
            buckets["very_likely"] += 1
        elif prob >= 50:
            buckets["likely"] += 1
        elif prob >= 25:
            buckets["possible"] += 1
        else:
            buckets["unlikely"] += 1

    return {
        "total_leads_analyzed": len(rows),
        "expected_conversions": round(expected_conversions, 1),
        "very_likely_count": buckets["very_likely"],
        "likely_count": buckets["likely"],
        "possible_count": buckets["possible"],
        "unlikely_count": buckets["unlikely"],
    }


# ============================================================
# 3. NEXT BEST ACTION (Rule-Based)
# ============================================================

def get_next_best_action(lead_id):
    """Recommend the single best next action for a lead based on signals."""
    rows = _get_lead_signals(lead_id)
    if not rows:
        return None

    best_row = max(rows, key=lambda r: calculate_conversion_probability(r))
    prob = calculate_conversion_probability(best_row)
    intent = best_row.get("buyer_intent")
    sentiment = best_row.get("final_sentiment")
    quality = best_row.get("quality_score") or 0

    # Rule-based decision tree
    if intent == "ready_to_buy" or prob >= 75:
        action = "Call immediately to close — high conversion signal"
        priority = "Urgent"
    elif intent == "actively_considering" and sentiment in ("positive", "very_positive"):
        action = "Send proposal/pricing details and schedule follow-up call within 2 days"
        priority = "High"
    elif intent == "actively_considering":
        action = "Follow up call to address remaining concerns"
        priority = "High"
    elif intent == "researching":
        action = "Send educational content (case studies, comparisons) to build trust"
        priority = "Medium"
    elif intent == "skeptical":
        action = "Address objections directly — consider a different agent or angle"
        priority = "Medium"
    elif intent == "not_interested":
        action = "Deprioritize — move to long-term nurture list"
        priority = "Low"
    else:
        action = "Re-engage with a discovery call to assess current interest"
        priority = "Medium"

    if quality < 40:
        action += " (Note: call quality was low — consider reassigning to a stronger agent)"

    return {
        "lead_id": lead_id,
        "recommended_action": action,
        "priority": priority,
        "conversion_probability": prob,
        "buyer_intent": intent,
    }


def get_action_queue(limit=15):
    """Get a prioritized action list across all leads."""
    rows = _get_lead_signals()
    seen_leads = set()
    actions = []

    for r in rows:
        lid = r["lead_id"]
        if lid in seen_leads:
            continue
        seen_leads.add(lid)

        action_data = get_next_best_action(lid)
        if action_data:
            actions.append(action_data)

    priority_order = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}
    actions.sort(key=lambda x: (priority_order.get(x["priority"], 4), -x["conversion_probability"]))

    return actions[:limit]


# ============================================================
# 4. SITE VISIT PROBABILITY
# ============================================================

def calculate_site_visit_probability(row):
    """
    Estimate likelihood of an in-person site visit based on engagement,
    intent, and sentiment — visits typically follow strong buying signals.
    """
    score = 0

    intent = row.get("buyer_intent")
    if intent == "ready_to_buy":
        score += 50
    elif intent == "actively_considering":
        score += 30
    elif intent == "researching":
        score += 10

    engagement = row.get("engagement_level")
    if engagement == "high":
        score += 25
    elif engagement == "medium":
        score += 10

    sentiment = row.get("final_sentiment")
    if sentiment in ("positive", "very_positive"):
        score += 15

    quality = row.get("quality_score") or 0
    if quality >= 70:
        score += 10

    return max(0, min(100, score))


def get_site_visit_predictions(limit=15):
    """Get leads ranked by site visit probability."""
    rows = _get_lead_signals()

    results = []
    for r in rows:
        prob = calculate_site_visit_probability(r)
        results.append({
            "lead_id": r["lead_id"],
            "call_id": r["call_id"],
            "agent_name": r["agent_name"],
            "site_visit_probability": prob,
            "buyer_intent": r["buyer_intent"],
        })

    results.sort(key=lambda x: x["site_visit_probability"], reverse=True)
    return results[:limit]


def get_lead_site_visit_probability(lead_id):
    """Get site visit probability for one specific lead."""
    rows = _get_lead_signals(lead_id)
    if not rows:
        return None

    best_row = max(rows, key=lambda r: calculate_site_visit_probability(r))
    prob = calculate_site_visit_probability(best_row)

    return {
        "lead_id": lead_id,
        "site_visit_probability": prob,
        "buyer_intent": best_row.get("buyer_intent"),
        "engagement": best_row.get("engagement_level"),
    }


# Quick self-test
if __name__ == "__main__":
    print("=== Sales Predictions (Top 5) ===")
    for p in get_sales_predictions(5):
        print(f"  Lead {p['lead_id']}: {p['conversion_probability']}% probability ({p['buyer_intent']})")

    print("\n=== Conversion Forecast ===")
    print(get_conversion_forecast())

    print("\n=== Action Queue (Top 5) ===")
    for a in get_action_queue(5):
        print(f"  Lead {a['lead_id']} [{a['priority']}]: {a['recommended_action']}")

    print("\n=== Site Visit Predictions (Top 5) ===")
    for s in get_site_visit_predictions(5):
        print(f"  Lead {s['lead_id']}: {s['site_visit_probability']}% likely")