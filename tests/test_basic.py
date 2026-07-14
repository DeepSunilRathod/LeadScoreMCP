"""
tests/test_basic.py — Basic smoke tests to verify core modules import correctly.
Run: pytest tests/
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Verify core modules can be imported without errors."""
    import config
    from lib import db, gemini, leads, saved_analysis, notifications, auth
    from agents import call_analysis, intent_sentiment, predictions
    assert True


def test_lead_scoring_logic():
    """Test the scoring function with known inputs."""
    from lib.leads import calculate_score, get_lead_category

    call = {
        "call_duration_sec": 400,
        "status": "Completed",
        "recording_url": "http://example.com/rec.mp3",
        "call_type": "Incoming",
    }
    score = calculate_score(call)
    assert score == 100  # 40 (duration) + 30 (status) + 10 (recording) + 20 (incoming)
    assert get_lead_category(score) == "Hot"


def test_lead_category_boundaries():
    from lib.leads import get_lead_category

    assert get_lead_category(21) == "Hot"
    assert get_lead_category(20) == "Warm"
    assert get_lead_category(11) == "Warm"
    assert get_lead_category(10) == "Cold"