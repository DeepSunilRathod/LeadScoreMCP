"""
lib/export_report.py — Export saved analysis data to CSV files
"""

import sys
import os
import csv
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import query

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")


def export_call_quality_report():
    """Export all call quality analyses to a CSV file."""
    os.makedirs(EXPORT_DIR, exist_ok=True)

    rows = query(
        """
        SELECT ca.call_id, c.lead_id, c.agent_name, c.call_date,
               ca.quality_score, ca.agent_technique, ca.engagement_quality,
               ca.call_outcome, ca.recommendation
        FROM call_analyses ca
        JOIN calls c ON ca.call_id = c.id
        ORDER BY ca.quality_score DESC
        """
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(EXPORT_DIR, f"call_quality_report_{timestamp}.csv")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    return filepath, len(rows)


def export_intent_report():
    """Export all intent/sentiment analyses to a CSV file."""
    os.makedirs(EXPORT_DIR, exist_ok=True)

    rows = query(
        """
        SELECT isa.call_id, isa.lead_id, c.agent_name, isa.buyer_intent,
               isa.initial_sentiment, isa.final_sentiment, isa.engagement_level,
               isa.readiness_score, isa.key_reason
        FROM intent_sentiment_analyses isa
        JOIN calls c ON isa.call_id = c.id
        ORDER BY isa.readiness_score DESC
        """
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(EXPORT_DIR, f"intent_sentiment_report_{timestamp}.csv")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    return filepath, len(rows)