"""
config.py — Configuration loader for LeadScoreMCP
Loads database credentials and API keys from .env file
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Environment mode: "development" or "production"
ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"
PORT = int(os.getenv("PORT", 5000))

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "database": os.getenv("DB_NAME", "leads_db"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Gemini model to use
GEMINI_MODEL = "gemini-2.5-flash"

# Validate critical config on import
if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not found in .env file!")

if not DB_CONFIG["password"]:
    print("⚠️  WARNING: DB_PASSWORD not found in .env file!")
    

# Email configuration
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Twilio WhatsApp configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")    


# ============================================================
# STARTUP VALIDATION (Production Hardening)
# ============================================================

def validate_config():
    """Check that critical configuration is present. Warns but doesn't crash."""
    warnings = []

    if not GEMINI_API_KEY:
        warnings.append("GEMINI_API_KEY is missing — AI analysis features will fail")
    if not DB_CONFIG["password"]:
        warnings.append("DB_PASSWORD is missing — database connection may fail")
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        warnings.append("Gmail credentials missing — email features disabled")
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        warnings.append("Twilio credentials missing — WhatsApp features disabled")

    if warnings:
        print("Configuration warnings:", file=__import__("sys").stderr)
        for w in warnings:
            print(f"  - {w}", file=__import__("sys").stderr)

    return warnings


validate_config()