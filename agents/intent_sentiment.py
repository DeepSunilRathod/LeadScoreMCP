"""
agents/intent_sentiment.py — AI Intent & Sentiment Analysis Agent
Extracts buyer intent stage and sentiment progression from call transcripts.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.gemini import call_gemini_json


def analyze_intent_sentiment_batch(calls):
    """
    Analyze buyer intent & sentiment for a batch of calls.
    """
    if not calls:
        raise ValueError("No calls provided")

    transcript_block = ""
    for i, call in enumerate(calls, 1):
        transcript_block += f"\n\n=== CALL {i} ===\n"
        transcript_block += f"Lead ID: {call.get('lead_id', 'N/A')}\n"
        transcript_text = (call.get("transcript") or "")[:1200]
        transcript_block += f"Transcript:\n{transcript_text}\n"

    prompt = f"""You are a sales psychology expert specializing in buyer intent and emotional intelligence.

IMPORTANT: These transcripts may be in Hindi, English, Urdu, Telugu, or Hinglish (mixed).
Analyze ALL transcripts regardless of language. Translate your analysis into English.

Analyze the following {len(calls)} sales call transcripts for buyer intent and sentiment:
{transcript_block}

For EACH call, identify:
1. Buyer Intent: ready_to_buy, actively_considering, researching, skeptical, or not_interested
2. Initial Sentiment: positive, neutral, or negative
3. Final Sentiment: positive, neutral, or negative
4. Engagement Level: high, medium, or low
5. Readiness Score (0-100): likelihood to purchase

Return ONLY valid JSON (no markdown, no code fences):
{{
  "calls": [
    {{
      "call_number": 1,
      "buyer_intent": "researching",
      "initial_sentiment": "neutral",
      "final_sentiment": "negative",
      "engagement_level": "low",
      "readiness_score": 20,
      "key_reason": "brief explanation of the intent/sentiment assessment"
    }}
  ],
  "summary": {{
    "intent_distribution": {{
      "ready_to_buy": 0,
      "actively_considering": 0,
      "researching": 0,
      "skeptical": 0,
      "not_interested": 0
    }},
    "avg_readiness_score": 25,
    "insight": "overall observation about buyer intent patterns"
  }}
}}"""

    return call_gemini_json(prompt, max_tokens=6000)


def analyze_single_call_intent(call):
    """
    Deep-dive intent & sentiment analysis for a single call.
    """
    prompt = f"""You are a sales psychology expert.

IMPORTANT: This transcript may be in Hindi, English, Urdu, or mixed language.
Translate your analysis into English.

Lead ID: {call.get('lead_id', 'N/A')}
Transcript:
{call.get('transcript', '')}

Analyze buyer intent and sentiment progression through this call.

Return ONLY valid JSON:
{{
  "buyer_intent": "researching",
  "intent_reasoning": "why this intent stage was assigned",
  "initial_sentiment": "neutral",
  "final_sentiment": "negative",
  "sentiment_shift_reason": "what caused the sentiment to change",
  "engagement_level": "low",
  "readiness_score": 20,
  "positive_signals": [],
  "negative_signals": ["signal1"],
  "recommended_next_action": "what the agent should do next with this lead"
}}"""

    return call_gemini_json(prompt, max_tokens=6000)


# Quick self-test
if __name__ == "__main__":
    from lib.db import query

    print("Testing Intent & Sentiment Agent...")
    calls = query(
        "SELECT * FROM calls WHERE transcript_status = 'done' LIMIT 3"
    )

    if not calls:
        print("No transcribed calls found in database")
        sys.exit(1)

    print(f"Found {len(calls)} calls, analyzing...\n")

    result = analyze_intent_sentiment_batch(calls)

    print("Analysis complete!\n")
    print("Intent Distribution:", result["summary"]["intent_distribution"])
    print(f"Avg Readiness Score: {result['summary']['avg_readiness_score']}/100")
    print(f"Insight: {result['summary']['insight']}\n")

    for c in result["calls"]:
        print(f"Call {c['call_number']}: Intent={c['buyer_intent']}, Readiness={c['readiness_score']}/100")
        print(f"  {c['initial_sentiment']} -> {c['final_sentiment']} | Engagement: {c['engagement_level']}")
        print(f"  Reason: {c['key_reason']}\n")