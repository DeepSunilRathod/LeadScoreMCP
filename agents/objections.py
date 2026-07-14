"""
agents/objections.py — Objection pattern detection across transcripts.
Uses Gemini to scan a batch of transcripts and identify common objection themes.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import query
from lib.gemini import call_gemini_json

COMMON_KEYWORDS = ["price", "expensive", "cost", "competitor", "think about it", "not interested", "busy", "later", "no budget"]


def get_objection_keyword_counts():
    """
    Fast, non-AI pass: count how many transcripts mention common objection keywords.
    """
    calls = query("SELECT transcript FROM calls WHERE transcript_status = 'done'")

    counts = {kw: 0 for kw in COMMON_KEYWORDS}
    total = len(calls)

    for c in calls:
        text = (c["transcript"] or "").lower()
        for kw in COMMON_KEYWORDS:
            if kw in text:
                counts[kw] += 1

    return {
        "total_transcripts": total,
        "keyword_counts": counts,
    }


def analyze_objection_patterns(sample_size=15):
    """
    AI pass: take a sample of transcripts and ask Gemini to identify
    the most common objection THEMES (not just keywords) with examples.
    """
    calls = query(
        "SELECT id, transcript FROM calls WHERE transcript_status = 'done' ORDER BY RAND() LIMIT %s",
        [sample_size],
    )

    if not calls:
        return {"themes": [], "summary": "No transcripts available."}

    transcript_block = ""
    for i, c in enumerate(calls, 1):
        text = (c["transcript"] or "")[:800]
        transcript_block += f"\n\n=== CALL {i} ===\n{text}"

    prompt = f"""You are a sales analyst. Review these {len(calls)} sales call transcripts
(may be in Hindi, English, or mixed language) and identify the most common
objections customers raised.

{transcript_block}

Return ONLY valid JSON:
{{
  "themes": [
    {{
      "objection": "short name for this objection type",
      "frequency": "how many of the calls mentioned this (approximate count)",
      "example_quote": "a short English translation/paraphrase of a typical example"
    }}
  ],
  "summary": "one paragraph overall summary of objection patterns"
}}"""

    return call_gemini_json(prompt, max_tokens=2000)


if __name__ == "__main__":
    print("=== Keyword Counts (Fast) ===")
    print(get_objection_keyword_counts())

    print("\n=== AI Pattern Analysis (Sample) ===")
    result = analyze_objection_patterns(10)
    print(result)