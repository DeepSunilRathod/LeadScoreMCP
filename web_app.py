"""
web_app.py — Flask web dashboard for LeadScoreMCP
Reuses all existing lib/ and agents/ modules — no duplicate logic.
Run: py web_app.py
Then open: http://localhost:5000

PRODUCTION NOTES:
- Debug mode is now OFF by default (set FLASK_DEBUG=true in .env to enable locally).
- All routes require HTTP Basic Auth (set APP_USERNAME / APP_PASSWORD in .env).
- Never commit your .env file — add it to .gitignore.
"""

import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, Response

from lib.leads import (
    get_all_leads, get_hot_leads, get_warm_leads, get_cold_leads,
    get_top_10_leads, get_lead_detail, get_dashboard_stats,
    get_agent_performance, get_call_analytics, recommend_leads
)
from lib.saved_analysis import (
    get_call_quality_summary, get_quality_stats, get_intent_summary,
    get_intent_distribution, get_agent_quality_ranking, get_top_readiness_leads,
    get_lead_full_analysis, get_call_quality_by_id, get_intent_by_call_id,
    get_agent_leaderboard_table, get_outcome_breakdown_table, get_call_transcript,
    compare_agents, get_followup_candidates, search_transcripts,
    get_call_time_analysis, get_conversion_funnel, get_weekly_summary_data,
    get_agent_detail, get_quality_trend_weekly, get_readiness_trend_weekly
)
from agents.predictions import (
    get_sales_predictions, get_lead_prediction, get_conversion_forecast,
    get_next_best_action, get_action_queue,
    get_site_visit_predictions, get_lead_site_visit_probability
)
from lib.notifications import (
    send_followup_email, send_whatsapp_followup_by_lead,
    bulk_send_whatsapp_to_category
)
from lib.db import query
from lib.chatbot import answer_question

from lib.leads import add_lead_note, get_lead_notes, search_leads_and_calls
import csv
import io
from flask import Response
from lib.chatbot import answer_from_knowledge_base

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

APP_USERNAME = os.environ.get("APP_USERNAME", "Deep")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "Deep@123")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))

if APP_PASSWORD == "Deep@123":
    print("WARNING: APP_PASSWORD is not set in .env — using an insecure default. "
          "Set APP_USERNAME and APP_PASSWORD in your .env file before deploying.")

app = Flask(__name__)
app.secret_key = "leadscoremcp-secret-key-change-in-production"

from functools import wraps
from flask import session, redirect, url_for
from lib.auth import verify_login
from lib.saved_analysis import get_manager_analytics


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        user = verify_login(data.get("username"), data.get("password"))
        if user:
            session["user"] = user
            return jsonify({"success": True, "role": user["role"]}) if request.is_json else redirect(url_for("index"))
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/api/current-user")
def api_current_user():
    if "user" not in session:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "user": session["user"]})

@app.errorhandler(Exception)
def handle_error(e):
    import traceback
    print("ERROR:", traceback.format_exc())
    return jsonify({"error": True, "message": str(e)}), 500

@app.route("/api/manager-analytics")
@login_required
def api_manager_analytics():
    if session["user"]["role"] not in ("admin", "manager"):
        return jsonify({"error": True, "message": "Access denied — Admin/Manager only"}), 403
    return jsonify(get_manager_analytics())

@app.route("/api/ask-knowledge", methods=["POST"])
@login_required
def api_ask_knowledge():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"answer": "Please ask a question."})
    return jsonify(answer_from_knowledge_base(question))


# ============================================================
# AUTH
# ============================================================

def check_auth(username, password):
    return username == APP_USERNAME and password == APP_PASSWORD


def authenticate():
    return Response(
        "Login required", 401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ============================================================
# PAGE ROUTE
# ============================================================

@app.route("/")
@login_required
def index():
    return render_template("index.html", user_role=session["user"]["role"], username=session["user"]["username"])


# ============================================================
# API: DASHBOARD & LEADS
# ============================================================

@app.route("/api/dashboard-stats")
@requires_auth
def api_dashboard_stats():
    return jsonify(get_dashboard_stats())


@app.route("/api/leads")
def api_leads():
    category = request.args.get("category", "all")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 25))

    # Fetch a large batch, then slice for pagination (simple approach for our data size)
    if category == "hot":
        all_data = get_hot_leads(2000)
    elif category == "warm":
        all_data = get_warm_leads(2000)
    elif category == "cold":
        all_data = get_cold_leads(2000)
    else:
        all_data = get_all_leads(2000)

    total = len(all_data)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = all_data[start:end]

    return jsonify({
        "items": page_data,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    })


@app.route("/api/leads/top10")
@requires_auth
def api_top10():
    return jsonify(get_top_10_leads())


@app.route("/api/lead/<lead_id>")
@requires_auth
def api_lead_detail(lead_id):
    detail = get_lead_detail(lead_id)
    analysis = get_lead_full_analysis(lead_id)

    # Convert any datetime objects to strings so jsonify doesn't crash
    if analysis and analysis.get("calls"):
        for c in analysis["calls"]:
            if c.get("call_date") is not None:
                c["call_date"] = str(c["call_date"])

    if detail and detail.get("call_history"):
        for c in detail["call_history"]:
            for key in ("call_date",):
                if c.get(key) is not None:
                    c[key] = str(c[key])

    return jsonify({"detail": detail, "analysis": analysis})


@app.route("/api/recommend")
@requires_auth
def api_recommend():
    count = int(request.args.get("count", 5))
    return jsonify(recommend_leads(count))


# ============================================================
# API: CALL QUALITY
# ============================================================

@app.route("/api/quality-stats")
@requires_auth
def api_quality_stats():
    return jsonify(get_quality_stats())


@app.route("/api/quality-top")
@requires_auth
def api_quality_top():
    limit = int(request.args.get("limit", 10))
    return jsonify(get_call_quality_summary(limit))


@app.route("/api/quality/<call_id>")
@requires_auth
def api_quality_by_id(call_id):
    return jsonify(get_call_quality_by_id(call_id))


@app.route("/api/agent-leaderboard")
@requires_auth
def api_agent_leaderboard():
    return jsonify(get_agent_leaderboard_table())


@app.route("/api/outcome-breakdown")
@requires_auth
def api_outcome_breakdown():
    return jsonify(get_outcome_breakdown_table())


@app.route("/api/compare-agents")
@requires_auth
def api_compare_agents():
    a1 = request.args.get("agent1", "")
    a2 = request.args.get("agent2", "")
    return jsonify(compare_agents(a1, a2))


# ============================================================
# API: INTENT & SENTIMENT
# ============================================================

@app.route("/api/intent-distribution")
@requires_auth
def api_intent_distribution():
    return jsonify(get_intent_distribution())


@app.route("/api/intent-top")
@requires_auth
def api_intent_top():
    limit = int(request.args.get("limit", 10))
    return jsonify(get_intent_summary(limit))


@app.route("/api/intent/<call_id>")
@requires_auth
def api_intent_by_id(call_id):
    return jsonify(get_intent_by_call_id(call_id))


@app.route("/api/readiness-top")
@requires_auth
def api_readiness_top():
    limit = int(request.args.get("limit", 10))
    return jsonify(get_top_readiness_leads(limit))


# ============================================================
# API: PREDICTIONS
# ============================================================

@app.route("/api/predictions/sales")
@requires_auth
def api_sales_predictions():
    limit = int(request.args.get("limit", 15))
    return jsonify(get_sales_predictions(limit))


@app.route("/api/predictions/forecast")
@requires_auth
def api_forecast():
    return jsonify(get_conversion_forecast())


@app.route("/api/predictions/action-queue")
@requires_auth
def api_action_queue():
    limit = int(request.args.get("limit", 15))
    return jsonify(get_action_queue(limit))


@app.route("/api/predictions/site-visit")
@requires_auth
def api_site_visit():
    limit = int(request.args.get("limit", 15))
    return jsonify(get_site_visit_predictions(limit))


# ============================================================
# API: TOOLS
# ============================================================

@app.route("/api/transcript/<call_id>")
@requires_auth
def api_transcript(call_id):
    return jsonify(get_call_transcript(call_id))


@app.route("/api/search-transcripts")
@requires_auth
def api_search_transcripts():
    keyword = request.args.get("q", "")
    limit = int(request.args.get("limit", 15))
    return jsonify(search_transcripts(keyword, limit))


@app.route("/api/call-time-analysis")
@requires_auth
def api_call_time():
    return jsonify(get_call_time_analysis())


@app.route("/api/conversion-funnel")
@requires_auth
def api_funnel():
    return jsonify(get_conversion_funnel())


@app.route("/api/followup-reminders")
@requires_auth
def api_followup_reminders():
    min_readiness = int(request.args.get("min_readiness", 50))
    limit = int(request.args.get("limit", 15))
    return jsonify(get_followup_candidates(min_readiness, limit))


# ============================================================
# API: ACTIONS (Send Messages)
# ============================================================

@app.route("/api/send-whatsapp/<lead_id>", methods=["POST"])
@requires_auth
def api_send_whatsapp(lead_id):
    success, msg = send_whatsapp_followup_by_lead(lead_id)
    return jsonify({"success": success, "message": msg})


@app.route("/api/send-email/<lead_id>", methods=["POST"])
@requires_auth
def api_send_email(lead_id):
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"success": False, "message": "Email address required"}), 400
    success, msg = send_followup_email(lead_id, email)
    return jsonify({"success": success, "message": msg})


@app.route("/api/bulk-whatsapp/<category>", methods=["POST"])
@requires_auth
def api_bulk_whatsapp(category):
    limit = int(request.args.get("limit", 20))
    result = bulk_send_whatsapp_to_category(category.capitalize(), limit)
    return jsonify(result)


@app.route("/api/message-history")
@requires_auth
def api_message_history():
    lead_id = request.args.get("lead_id")
    limit = int(request.args.get("limit", 20))

    sql = "SELECT * FROM message_log"
    params = []
    if lead_id:
        sql += " WHERE lead_id = %s"
        params.append(lead_id)
    sql += " ORDER BY sent_at DESC LIMIT %s"
    params.append(limit)

    rows = query(sql, params)
    for r in rows:
        r["sent_at"] = str(r["sent_at"])
    return jsonify(rows)


# ============================================================
# HEALTH CHECK (no auth — used by uptime monitors/load balancers)
# ============================================================

@app.route("/health")
def health():
    return jsonify({"status": "ok"})



@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Please type a question.", "tool_used": None})

    result = answer_question(question)
    return jsonify(result)



@app.route("/api/lead/<lead_id>/notes", methods=["GET", "POST"])
def api_lead_notes(lead_id):
    if request.method == "POST":
        data = request.get_json()
        note = data.get("note", "").strip()
        if not note:
            return jsonify({"success": False, "message": "Note cannot be empty"}), 400
        add_lead_note(lead_id, note)
        return jsonify({"success": True})

    notes = get_lead_notes(lead_id)
    for n in notes:
        n["created_at"] = str(n["created_at"])
    return jsonify(notes)


@app.route("/api/search")
def api_global_search():
    term = request.args.get("q", "").strip()
    if not term:
        return jsonify([])
    results = search_leads_and_calls(term)
    for r in results:
        if r.get("call_date"):
            r["call_date"] = str(r["call_date"])
    return jsonify(results)


@app.route("/api/export/<table>")
def api_export_csv(table):
    """Generic CSV export for leads, quality, or intent tables."""
    if table == "leads":
        data = get_all_leads(1000)
    elif table == "quality":
        data = get_call_quality_summary(200)
    elif table == "intent":
        data = get_intent_summary(200)
    else:
        return jsonify({"error": "Unknown table"}), 400

    if not data:
        return jsonify({"error": "No data to export"}), 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table}_export.csv"},
    )

@app.route("/api/agent/<agent_name>")
def api_agent_detail(agent_name):
    detail = get_agent_detail(agent_name)
    for c in detail["calls"]:
        if c.get("call_date"):
            c["call_date"] = str(c["call_date"])
    return jsonify(detail)


@app.route("/api/trends/quality")
def api_quality_trend():
    rows = get_quality_trend_weekly()
    for r in rows:
        r["week_start"] = str(r["week_start"])
    return jsonify(rows)


@app.route("/api/trends/readiness")
def api_readiness_trend():
    rows = get_readiness_trend_weekly()
    for r in rows:
        r["week_start"] = str(r["week_start"])
    return jsonify(rows)


if __name__ == "__main__":
    from config import DEBUG, PORT
    print(f"Starting LeadScoreMCP Web Dashboard ({'DEBUG' if DEBUG else 'PROD'} mode)...")
    print(f"Open: http://localhost:{PORT}")
    app.run(debug=DEBUG, port=PORT)
    
    
    