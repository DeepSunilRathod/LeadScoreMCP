"""
lib/gemini.py — Google Gemini API wrapper (using new google-genai SDK)
Handles sending prompts to Gemini and parsing JSON responses
Includes retry logic for server overload + token usage logging.
"""

import sys
import os
import json
import time

# Add parent directory to path so we can import config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from config import GEMINI_API_KEY, GEMINI_MODEL

# Create the client (reused across calls)
_client = genai.Client(api_key=GEMINI_API_KEY)


def call_gemini(prompt, max_tokens=2000, temperature=0.3, max_retries=3):
    """
    Send a prompt to Gemini and get back raw text response.
    Retries automatically if the server is overloaded.
    Prints exact token usage for each successful call.
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                u = response.usage_metadata
                print(
                    f"[TOKENS] input={u.prompt_token_count}, "
                    f"output={u.candidates_token_count}, "
                    f"total={u.total_token_count}",
                    file=sys.stderr,
                )

            if hasattr(response, "candidates") and response.candidates:
                finish_reason = getattr(response.candidates[0], "finish_reason", None)
                print(f"[FINISH_REASON] {finish_reason}", file=sys.stderr)

            return response.text

        except ServerError as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, then 2s, then 4s
                print(
                    f"Gemini overloaded, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})",
                    file=sys.stderr,
                )
                time.sleep(wait_time)
            else:
                raise Exception(
                    "Gemini is currently overloaded (high demand). "
                    "Please try again in a minute."
                ) from last_error


def call_gemini_json(prompt, max_tokens=2000, temperature=0):
    """
    Send a prompt to Gemini and parse the response as JSON.
    Automatically strips markdown code fences if present.
    """
    text = call_gemini(prompt, max_tokens=max_tokens, temperature=temperature)

    # Clean up response - remove markdown code blocks if Gemini added them
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON from Gemini response: {e}")
        print(f"Raw response was:\n{text[:500]}")
        raise


# Quick self-test when running this file directly
if __name__ == "__main__":
    print("Testing Gemini API connection...")
    try:
        result = call_gemini("Say 'Hello, I am working!' and nothing else.")
        print(f"Gemini responded: {result}")
    except Exception as e:
        print(f"Gemini API failed: {e}")