"""
batch_process.py — Analyze ALL transcribed calls and save results to database.
Processes in small batches to stay within Gemini token limits.
Safe to re-run: skips calls that are already analyzed.
"""

import sys
import time
from lib.db import query, get_conn
from agents.call_analysis import analyze_call_batch
from agents.intent_sentiment import analyze_intent_sentiment_batch

BATCH_SIZE = 5  # calls per Gemini request — safe for token limits
DELAY_BETWEEN_BATCHES = 4  # seconds, to avoid rate limits


def get_unanalyzed_calls(table_name):
    """Get transcribed calls that don't have an entry in the given analysis table yet."""
    sql = f"""
        SELECT c.* FROM calls c
        LEFT JOIN {table_name} a ON c.id = a.call_id
        WHERE c.transcript_status = 'done' AND a.call_id IS NULL
    """
    return query(sql)


def save_call_analysis(call_id, result):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO call_analyses
        (call_id, quality_score, agent_technique, engagement_quality,
         call_outcome, strengths, areas_for_improvement, recommendation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        quality_score=VALUES(quality_score),
        agent_technique=VALUES(agent_technique),
        engagement_quality=VALUES(engagement_quality),
        call_outcome=VALUES(call_outcome),
        strengths=VALUES(strengths),
        areas_for_improvement=VALUES(areas_for_improvement),
        recommendation=VALUES(recommendation)
        """,
        (
            call_id,
            result["quality_score"],
            result["agent_technique"],
            result["engagement_quality"],
            result["call_outcome"],
            ", ".join(result["strengths"]),
            ", ".join(result["areas_for_improvement"]),
            result["recommendation"],
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def save_intent_analysis(call_id, lead_id, result):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO intent_sentiment_analyses
        (call_id, lead_id, buyer_intent, initial_sentiment, final_sentiment,
         engagement_level, readiness_score, key_reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        buyer_intent=VALUES(buyer_intent),
        initial_sentiment=VALUES(initial_sentiment),
        final_sentiment=VALUES(final_sentiment),
        engagement_level=VALUES(engagement_level),
        readiness_score=VALUES(readiness_score),
        key_reason=VALUES(key_reason)
        """,
        (
            call_id,
            lead_id,
            result["buyer_intent"],
            result["initial_sentiment"],
            result["final_sentiment"],
            result["engagement_level"],
            result["readiness_score"],
            result["key_reason"],
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def run_call_quality_batch():
    print("\n=== CALL QUALITY ANALYSIS ===")
    calls = get_unanalyzed_calls("call_analyses")
    print(f"Found {len(calls)} calls to analyze")

    if not calls:
        print("Nothing to do — all calls already analyzed!")
        return

    total_done = 0
    for i in range(0, len(calls), BATCH_SIZE):
        batch = calls[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(calls) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\nBatch {batch_num}/{total_batches} ({len(batch)} calls)...")

        try:
            result = analyze_call_batch(batch)

            for idx, c in enumerate(result["calls"]):
                call_id = batch[idx]["id"]
                save_call_analysis(call_id, c)
                total_done += 1

            print(f"  Saved {len(result['calls'])} results")

        except Exception as e:
            print(f"  ERROR on batch {batch_num}: {e}")
            print(f"  Skipping this batch, continuing...")

        time.sleep(DELAY_BETWEEN_BATCHES)

    print(f"\nCall quality analysis complete! {total_done} calls processed.")


def run_intent_sentiment_batch():
    print("\n=== INTENT & SENTIMENT ANALYSIS ===")
    calls = get_unanalyzed_calls("intent_sentiment_analyses")
    print(f"Found {len(calls)} calls to analyze")

    if not calls:
        print("Nothing to do — all calls already analyzed!")
        return

    total_done = 0
    for i in range(0, len(calls), BATCH_SIZE):
        batch = calls[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(calls) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\nBatch {batch_num}/{total_batches} ({len(batch)} calls)...")

        try:
            result = analyze_intent_sentiment_batch(batch)

            for idx, c in enumerate(result["calls"]):
                call_id = batch[idx]["id"]
                lead_id = batch[idx]["lead_id"]
                save_intent_analysis(call_id, lead_id, c)
                total_done += 1

            print(f"  Saved {len(result['calls'])} results")

        except Exception as e:
            print(f"  ERROR on batch {batch_num}: {e}")
            print(f"  Skipping this batch, continuing...")

        time.sleep(DELAY_BETWEEN_BATCHES)

    print(f"\nIntent/sentiment analysis complete! {total_done} calls processed.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "quality"):
        run_call_quality_batch()

    if mode in ("all", "intent"):
        run_intent_sentiment_batch()

    print("\nAll done!")