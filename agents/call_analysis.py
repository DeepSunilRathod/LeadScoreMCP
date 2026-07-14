"""
agents/call_analysis.py — AI Call Quality Analysis Agent
Analyzes sales call transcripts for quality, technique, and outcomes.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.gemini import call_gemini_json


def analyze_call_batch(calls):
    """
    Analyze a batch of calls (list of dicts with 'transcript', 'agent_name', etc.)
    Returns quality scores, technique ratings, and recommendations for each call.
    """
    if not calls:
        raise ValueError("No calls provided")

    transcript_block = ""
    for i, call in enumerate(calls, 1):
        transcript_block += f"\n\n=== CALL {i} ===\n"
        transcript_block += f"Agent: {call.get('agent_name', 'Unknown')}\n"
        transcript_block += f"Lead ID: {call.get('lead_id', 'N/A')}\n"
        transcript_block += f"Duration: {call.get('call_duration_sec', 0)}s\n"
        transcript_text = (call.get("transcript") or "")[:1200]
        transcript_block += f"Transcript:\n{transcript_text}\n"

    prompt = f"""You are a sales call quality analyzer. You ONLY analyze the call transcript data given below. You do not answer general knowledge questions, opinions, or anything unrelated to these calls.

IMPORTANT RULES:
- These transcripts may be in Hindi, English, Urdu, Telugu, or Hinglish. Analyze ALL transcripts regardless of language, but write your output in English.
- Do NOT add explanations, theory, or extra commentary. Only fill in the exact fields requested.
- Keep every text field short and direct (max 12 words per field).
- Base every answer strictly on the transcript text. Do not guess or invent information not present in the transcript.
- If a transcript is empty or too short to analyze, still return the JSON structure with your best-effort values, do not skip it.

Analyze the following {len(calls)} sales call transcripts:
{transcript_block}

For EACH call, evaluate:
1. Quality Score (0-100)
2. Agent Technique (0-10)
3. Engagement Quality (0-10)
4. Call Outcome: successful, unsuccessful, or partial
5. Strengths and areas for improvement (short phrases, not sentences)
6. One specific actionable recommendation (max 12 words)

Return ONLY valid JSON (no markdown, no code fences, no text before or after the JSON):
{{
  "calls": [
    {{
      "call_number": 1,
      "quality_score": 75,
      "agent_technique": 7,
      "engagement_quality": 8,
      "call_outcome": "successful",
      "strengths": ["strength1", "strength2"],
      "areas_for_improvement": ["area1"],
      "recommendation": "specific actionable tip"
    }}
  ],
  "summary": {{
    "average_quality_score": 72,
    "success_rate": 0.6,
    "team_pattern": "overall observation about these calls, max 15 words"
  }}
}}"""

    return call_gemini_json(prompt, max_tokens=8000)


def analyze_single_call(call):
    """
    Deep-dive analysis of a single call transcript.
    """
    prompt = f"""You are a sales call quality analyzer. You ONLY analyze the call transcript data given below. You do not answer general knowledge questions, opinions, or anything unrelated to this call.

IMPORTANT RULES:
- This transcript may be in Hindi, English, Urdu, or mixed language. Write your output in English.
- Do NOT add explanations, theory, or extra commentary. Only fill in the exact fields requested.
- Keep every text field short and direct (max 12 words per field).
- Base every answer strictly on the transcript text. Do not guess or invent information not present in the transcript.

Agent: {call.get('agent_name', 'Unknown')}
Duration: {call.get('call_duration_sec', 0)}s

Transcript:
{call.get('transcript', '')}

Return ONLY valid JSON (no markdown, no code fences, no text before or after the JSON):
{{
  "quality_score": 75,
  "agent_technique": 7,
  "engagement_quality": 8,
  "call_outcome": "successful",
  "outcome_reason": "why this outcome, max 12 words",
  "strengths": ["strength1", "strength2"],
  "improvements": ["improvement1"],
  "top_recommendation": "single most valuable tip, max 12 words",
  "next_action": "what should happen next, max 10 words"
}}"""

    return call_gemini_json(prompt, max_tokens=8000)

def generate_meeting_summary(call):
    """Generate a structured post-call summary: summary, key points, mood, objections."""
    prompt = f"""Summarize this sales call (may be Hindi/English/mixed):

Transcript: {call.get('transcript', '')}

Return ONLY valid JSON:
{{
  "summary": "2-3 sentence overview in English",
  "key_points": ["point1", "point2", "point3"],
  "customer_mood": "positive|neutral|negative",
  "objections": ["objection1", "objection2"]
}}"""
    return call_gemini_json(prompt, max_tokens=1000)


# Quick self-test
if __name__ == "__main__":
    from lib.db import query

    print("Testing Call Analysis Agent...")
    calls = query(
        "SELECT * FROM calls WHERE transcript_status = 'done' LIMIT 3"
    )

    if not calls:
        print("No transcribed calls found in database")
        sys.exit(1)

    print(f"Found {len(calls)} calls, analyzing...\n")

    result = analyze_call_batch(calls)

    print("Analysis complete!\n")
    print(f"Average Quality: {result['summary']['average_quality_score']}/100")
    print(f"Success Rate: {result['summary']['success_rate'] * 100:.1f}%")
    print(f"Team Pattern: {result['summary']['team_pattern']}\n")

    for c in result["calls"]:
        print(f"Call {c['call_number']}: Quality={c['quality_score']}, Outcome={c['call_outcome']}")
        print(f"  Recommendation: {c['recommendation']}\n")