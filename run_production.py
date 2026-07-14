"""
run_production.py — Production server entry point using Waitress
(instead of Flask's built-in dev server).

Run:
    py run_production.py
"""

from waitress import serve
from web_app import app
from config import PORT, DEBUG

if __name__ == "__main__":
    print(f"Starting LeadScoreMCP in PRODUCTION mode on port {PORT}...")
    print(f"Open: http://localhost:{PORT}")
    serve(app, host="0.0.0.0", port=PORT, threads=6)