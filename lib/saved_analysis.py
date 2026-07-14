"""
lib/saved_analysis.py — Query pre-computed AI analysis (instant, no Gemini calls)
Reads from call_analyses and intent_sentiment_analyses tables.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import query


def get_call_quality_summary(limit=10):
    """Get saved call quality results, formatted as table rows."""
    rows = query(
        """
        SELECT ca.call_id, ca.quality_score, ca.agent_technique, ca.engagement_quality,
               ca.call_outcome, ca.recommendation, c.agent_name, c.lead_id
        FROM call_analyses ca
        JOIN calls c ON ca.call_id = c.id
        ORDER BY ca.quality_score DESC
        LIMIT %s
        """,
        [limit],
    )
    return rows


def get_quality_stats():
    """Overall stats from saved call quality analyses."""
    row = query(
        """
        SELECT
            COUNT(*) as total_analyzed,
            ROUND(AVG(quality_score), 1) as avg_quality,
            ROUND(AVG(agent_technique), 1) as avg_technique,
            ROUND(AVG(engagement_quality), 1) as avg_engagement,
            SUM(CASE WHEN call_outcome = 'successful' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN call_outcome = 'partial' THEN 1 ELSE 0 END) as partial,
            SUM(CASE WHEN call_outcome = 'unsuccessful' THEN 1 ELSE 0 END) as unsuccessful
        FROM call_analyses
        """
    )
    return row[0] if row else None


def get_intent_summary(limit=10):
    """Get saved intent/sentiment results, formatted as table rows."""
    rows = query(
        """
        SELECT isa.call_id, isa.lead_id, isa.buyer_intent, isa.initial_sentiment,
               isa.final_sentiment, isa.engagement_level, isa.readiness_score, isa.key_reason
        FROM intent_sentiment_analyses isa
        ORDER BY isa.readiness_score DESC
        LIMIT %s
        """,
        [limit],
    )
    return rows


def get_intent_distribution():
    """Count of leads by buyer intent category, from saved data."""
    rows = query(
        """
        SELECT buyer_intent, COUNT(*) as count, ROUND(AVG(readiness_score), 1) as avg_readiness
        FROM intent_sentiment_analyses
        GROUP BY buyer_intent
        ORDER BY count DESC
        """
    )
    return rows


def get_agent_quality_ranking():
    """Rank agents by average call quality score, from saved data."""
    rows = query(
        """
        SELECT c.agent_name,
               COUNT(*) as calls_analyzed,
               ROUND(AVG(ca.quality_score), 1) as avg_quality,
               SUM(CASE WHEN ca.call_outcome = 'successful' THEN 1 ELSE 0 END) as successful_calls
        FROM call_analyses ca
        JOIN calls c ON ca.call_id = c.id
        GROUP BY c.agent_name
        ORDER BY avg_quality DESC
        """
    )
    return rows


def get_top_readiness_leads(limit=10):
    """Leads with highest purchase readiness score, from saved intent analysis."""
    rows = query(
        """
        SELECT isa.lead_id, isa.call_id, isa.buyer_intent, isa.readiness_score,
               isa.engagement_level, isa.key_reason, c.agent_name
        FROM intent_sentiment_analyses isa
        JOIN calls c ON isa.call_id = c.id
        ORDER BY isa.readiness_score DESC
        LIMIT %s
        """,
        [limit],
    )
    return rows


def get_lead_full_analysis(lead_id):
    """
    Get ALL saved analysis (quality + intent/sentiment) for a lead,
    MERGED by call_id into single rows — ready for table display.
    """
    lead_id = str(lead_id)

    rows = query(
        """
        SELECT
            c.id AS call_id,
            c.call_date,
            c.agent_name,
            ca.quality_score,
            ca.call_outcome,
            ca.recommendation,
            isa.buyer_intent,
            isa.readiness_score,
            isa.initial_sentiment,
            isa.final_sentiment,
            isa.engagement_level
        FROM calls c
        LEFT JOIN call_analyses ca ON c.id = ca.call_id
        LEFT JOIN intent_sentiment_analyses isa ON c.id = isa.call_id
        WHERE c.lead_id = %s
        AND (ca.call_id IS NOT NULL OR isa.call_id IS NOT NULL)
        ORDER BY c.call_date DESC
        """,
        [lead_id],
    )

    if not rows:
        return None

    return {
        "lead_id": lead_id,
        "calls": rows,
    }


def get_call_quality_by_id(call_id):
    """Get saved quality analysis for ONE specific call_id."""
    rows = query(
        """
        SELECT ca.call_id, ca.quality_score, ca.agent_technique, ca.engagement_quality,
               ca.call_outcome, ca.strengths, ca.areas_for_improvement, ca.recommendation,
               c.agent_name, c.lead_id, c.call_date, c.call_duration_sec
        FROM call_analyses ca
        JOIN calls c ON ca.call_id = c.id
        WHERE ca.call_id = %s
        """,
        [call_id],
    )
    return rows[0] if rows else None


def get_intent_by_call_id(call_id):
    """Get saved intent/sentiment analysis for ONE specific call_id."""
    rows = query(
        """
        SELECT isa.call_id, isa.lead_id, isa.buyer_intent, isa.initial_sentiment,
               isa.final_sentiment, isa.engagement_level, isa.readiness_score, isa.key_reason
        FROM intent_sentiment_analyses isa
        WHERE isa.call_id = %s
        """,
        [call_id],
    )
    return rows[0] if rows else None


def get_agent_leaderboard_table():
    """Full agent comparison — quality, intent success, hot leads, all in one query."""
    rows = query(
        """
        SELECT
            c.agent_name,
            COUNT(DISTINCT c.id) as total_calls,
            ROUND(AVG(ca.quality_score), 1) as avg_quality,
            SUM(CASE WHEN ca.call_outcome = 'successful' THEN 1 ELSE 0 END) as successful_calls,
            ROUND(AVG(isa.readiness_score), 1) as avg_readiness
        FROM calls c
        LEFT JOIN call_analyses ca ON c.id = ca.call_id
        LEFT JOIN intent_sentiment_analyses isa ON c.id = isa.call_id
        WHERE ca.call_id IS NOT NULL OR isa.call_id IS NOT NULL
        GROUP BY c.agent_name
        ORDER BY avg_quality DESC
        """
    )
    return rows


def get_outcome_breakdown_table():
    """Call outcome distribution with average readiness per outcome."""
    rows = query(
        """
        SELECT
            ca.call_outcome,
            COUNT(*) as call_count,
            ROUND(AVG(ca.quality_score), 1) as avg_quality
        FROM call_analyses ca
        GROUP BY ca.call_outcome
        ORDER BY call_count DESC
        """
    )
    return rows


def get_call_transcript(call_id):
    """Get the raw transcript text for a specific call."""
    rows = query(
        """
        SELECT c.id, c.lead_id, c.agent_name, c.call_date, c.call_duration_sec,
               c.transcript, c.transcript_status
        FROM calls c
        WHERE c.id = %s
        """,
        [call_id],
    )
    return rows[0] if rows else None


def compare_agents(agent1, agent2):
    """Side-by-side comparison of two agents' performance."""
    def get_stats(agent_name):
        rows = query(
            """
            SELECT
                COUNT(DISTINCT c.id) as total_calls,
                ROUND(AVG(ca.quality_score), 1) as avg_quality,
                ROUND(AVG(ca.agent_technique), 1) as avg_technique,
                ROUND(AVG(ca.engagement_quality), 1) as avg_engagement,
                SUM(CASE WHEN ca.call_outcome = 'successful' THEN 1 ELSE 0 END) as successful,
                ROUND(AVG(isa.readiness_score), 1) as avg_readiness
            FROM calls c
            LEFT JOIN call_analyses ca ON c.id = ca.call_id
            LEFT JOIN intent_sentiment_analyses isa ON c.id = isa.call_id
            WHERE c.agent_name LIKE %s AND (ca.call_id IS NOT NULL OR isa.call_id IS NOT NULL)
            """,
            [f"%{agent_name}%"],
        )
        return rows[0] if rows else None

    return {
        "agent1_name": agent1,
        "agent1_stats": get_stats(agent1),
        "agent2_name": agent2,
        "agent2_stats": get_stats(agent2),
    }


def get_followup_candidates(min_readiness=50, limit=15):
    """
    Leads with high readiness score but call happened a while ago —
    candidates for follow-up. Uses days since last call as urgency signal.
    """
    rows = query(
        """
        SELECT
            isa.lead_id, isa.call_id, isa.buyer_intent, isa.readiness_score,
            isa.engagement_level, c.agent_name, c.call_date,
            DATEDIFF(NOW(), c.call_date) as days_since_call
        FROM intent_sentiment_analyses isa
        JOIN calls c ON isa.call_id = c.id
        WHERE isa.readiness_score >= %s
        ORDER BY isa.readiness_score DESC, days_since_call DESC
        LIMIT %s
        """,
        [min_readiness, limit],
    )
    return rows


def search_transcripts(keyword, limit=15):
    """Search transcript text for a keyword across all calls."""
    rows = query(
        """
        SELECT c.id, c.lead_id, c.agent_name, c.call_date, c.transcript
        FROM calls c
        WHERE c.transcript_status = 'done'
        AND c.transcript LIKE %s
        LIMIT %s
        """,
        [f"%{keyword}%", limit],
    )

    results = []
    for r in rows:
        text = r["transcript"] or ""
        idx = text.lower().find(keyword.lower())
        if idx >= 0:
            start = max(0, idx - 60)
            end = min(len(text), idx + len(keyword) + 60)
            snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
        else:
            snippet = text[:120]

        results.append({
            "call_id": r["id"],
            "lead_id": r["lead_id"],
            "agent_name": r["agent_name"],
            "call_date": r["call_date"],
            "snippet": snippet,
        })
    return results


def get_call_time_analysis():
    """Analyze which hours/days have the best connect rate and quality."""
    rows = query(
        """
        SELECT
            HOUR(call_date) as call_hour,
            COUNT(*) as total_calls,
            SUM(CASE WHEN status IN ('Completed', 'ANSWERED') THEN 1 ELSE 0 END) as connected,
            ROUND(AVG(call_duration_sec), 0) as avg_duration
        FROM calls
        WHERE call_date IS NOT NULL AND source = 'primary'
        GROUP BY HOUR(call_date)
        ORDER BY call_hour
        """
    )
    return rows


def get_conversion_funnel():
    """
    Funnel view: Total Leads -> Connected -> Transcribed -> Analyzed by Intent stage.
    Combines calls table + intent_sentiment_analyses.
    """
    total_leads = query("SELECT COUNT(*) as c FROM calls WHERE source = 'primary'")[0]["c"]
    connected = query(
        "SELECT COUNT(*) as c FROM calls WHERE source = 'primary' AND status IN ('Completed', 'ANSWERED')"
    )[0]["c"]
    transcribed = query(
        "SELECT COUNT(*) as c FROM calls WHERE transcript_status = 'done'"
    )[0]["c"]

    intent_counts = query(
        """
        SELECT buyer_intent, COUNT(*) as count
        FROM intent_sentiment_analyses
        GROUP BY buyer_intent
        """
    )
    intent_map = {r["buyer_intent"]: r["count"] for r in intent_counts}

    return {
        "total_leads": total_leads,
        "connected": connected,
        "transcribed": transcribed,
        "ready_to_buy": intent_map.get("ready_to_buy", 0),
        "actively_considering": intent_map.get("actively_considering", 0),
        "researching": intent_map.get("researching", 0),
        "skeptical": intent_map.get("skeptical", 0),
        "not_interested": intent_map.get("not_interested", 0),
    }


def get_weekly_summary_data():
    """Combine key stats for a summary report."""
    quality_stats = get_quality_stats()
    intent_dist = get_intent_distribution()
    top_leads = get_top_readiness_leads(5)
    agent_ranking = get_agent_quality_ranking()

    return {
        "quality_stats": quality_stats,
        "intent_distribution": intent_dist,
        "top_leads": top_leads,
        "agent_ranking": agent_ranking,
    }


def get_agent_detail(agent_name):
    """Full detail for one agent: stats + call history + notes-worthy calls."""
    calls = query(
        """
        SELECT c.id as call_id, c.lead_id, c.call_date, c.status, c.call_duration_sec,
               ca.quality_score, ca.call_outcome, ca.recommendation,
               isa.buyer_intent, isa.readiness_score
        FROM calls c
        LEFT JOIN call_analyses ca ON c.id = ca.call_id
        LEFT JOIN intent_sentiment_analyses isa ON c.id = isa.call_id
        WHERE c.agent_name = %s
        ORDER BY c.call_date DESC
        LIMIT 100
        """,
        [agent_name],
    )

    analyzed = [c for c in calls if c["quality_score"] is not None]
    avg_quality = round(sum(c["quality_score"] for c in analyzed) / len(analyzed), 1) if analyzed else 0
    successful = sum(1 for c in analyzed if c["call_outcome"] == "successful")

    return {
        "agent_name": agent_name,
        "total_calls": len(calls),
        "analyzed_calls": len(analyzed),
        "avg_quality": avg_quality,
        "successful_calls": successful,
        "calls": calls,
    }


def get_quality_trend_weekly():
    """Average quality score bucketed by week, for trend charting."""
    rows = query(
        """
        SELECT
            YEARWEEK(c.call_date, 1) as year_week,
            MIN(DATE(c.call_date)) as week_start,
            ROUND(AVG(ca.quality_score), 1) as avg_quality,
            COUNT(*) as call_count
        FROM call_analyses ca
        JOIN calls c ON ca.call_id = c.id
        WHERE c.call_date IS NOT NULL
        GROUP BY YEARWEEK(c.call_date, 1)
        ORDER BY year_week ASC
        """
    )
    return rows


def get_readiness_trend_weekly():
    """Average readiness score bucketed by week."""
    rows = query(
        """
        SELECT
            YEARWEEK(c.call_date, 1) as year_week,
            MIN(DATE(c.call_date)) as week_start,
            ROUND(AVG(isa.readiness_score), 1) as avg_readiness,
            COUNT(*) as call_count
        FROM intent_sentiment_analyses isa
        JOIN calls c ON isa.call_id = c.id
        WHERE c.call_date IS NOT NULL
        GROUP BY YEARWEEK(c.call_date, 1)
        ORDER BY year_week ASC
        """
    )
    return rows

def get_manager_analytics():
    """Key metrics managers care about, all in one call."""
    best_agent = query(
        """
        SELECT c.agent_name, ROUND(AVG(ca.quality_score), 1) as avg_quality, COUNT(*) as calls
        FROM call_analyses ca JOIN calls c ON ca.call_id = c.id
        GROUP BY c.agent_name ORDER BY avg_quality DESC LIMIT 1
        """
    )

    most_lost_agent = query(
        """
        SELECT c.agent_name, COUNT(*) as lost_count
        FROM call_analyses ca JOIN calls c ON ca.call_id = c.id
        WHERE ca.call_outcome = 'unsuccessful'
        GROUP BY c.agent_name ORDER BY lost_count DESC LIMIT 1
        """
    )

    avg_call_time = query(
        "SELECT ROUND(AVG(call_duration_sec), 0) as avg_sec FROM calls WHERE source = 'primary' AND call_duration_sec > 0"
    )

    avg_sentiment = query(
        """
        SELECT
          SUM(CASE WHEN final_sentiment IN ('positive','very_positive') THEN 1 ELSE 0 END) as positive,
          SUM(CASE WHEN final_sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral,
          SUM(CASE WHEN final_sentiment IN ('negative','very_negative') THEN 1 ELSE 0 END) as negative,
          COUNT(*) as total
        FROM intent_sentiment_analyses
        """
    )

    conversion_rate = query(
        """
        SELECT
          SUM(CASE WHEN call_outcome = 'successful' THEN 1 ELSE 0 END) as successful,
          COUNT(*) as total
        FROM call_analyses
        """
    )

    return {
        "best_salesperson": best_agent[0] if best_agent else None,
        "most_lost_leads_agent": most_lost_agent[0] if most_lost_agent else None,
        "avg_call_time_sec": avg_call_time[0]["avg_sec"] if avg_call_time else 0,
        "sentiment_breakdown": avg_sentiment[0] if avg_sentiment else None,
        "conversion_rate": round(
            conversion_rate[0]["successful"] / conversion_rate[0]["total"] * 100, 1
        ) if conversion_rate and conversion_rate[0]["total"] else 0,
    }
    
    

# Quick self-test
if __name__ == "__main__":
    print("=== Quality Stats ===")
    print(get_quality_stats())

    print("\n=== Top 5 Quality Calls ===")
    for r in get_call_quality_summary(5):
        print(f"  Call {r['call_id']}: {r['quality_score']}/100 - {r['agent_name']} - {r['call_outcome']}")

    print("\n=== Intent Distribution ===")
    for r in get_intent_distribution():
        print(f"  {r['buyer_intent']}: {r['count']} leads (avg readiness: {r['avg_readiness']})")

    print("\n=== Agent Quality Ranking ===")
    for r in get_agent_quality_ranking():
        print(f"  {r['agent_name']}: {r['avg_quality']}/100 avg ({r['calls_analyzed']} calls, {r['successful_calls']} successful)")