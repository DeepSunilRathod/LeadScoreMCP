#!/usr/bin/env python3
"""
mcp_server.py — LeadScoreMCP Server
Exposes Call Analysis and Intent/Sentiment tools to Claude Desktop.
"""

import asyncio
import json
import sys

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    raise SystemExit("Run: py -m pip install mcp")

from lib.db import query
from agents.call_analysis import analyze_call_batch, analyze_single_call
from agents.intent_sentiment import analyze_intent_sentiment_batch, analyze_single_call_intent
from lib.leads import (
    get_all_leads, get_hot_leads, get_warm_leads, get_cold_leads,
    get_top_10_leads, get_lead_detail, get_dashboard_stats,
    get_agent_performance, get_call_analytics, recommend_leads,
    find_duplicate_phone_numbers
)
from lib.saved_analysis import (
    get_call_quality_summary, get_quality_stats, get_intent_summary,
    get_intent_distribution, get_agent_quality_ranking, get_top_readiness_leads,
    get_lead_full_analysis, get_call_quality_by_id, get_intent_by_call_id,
    get_agent_leaderboard_table, get_outcome_breakdown_table, get_call_transcript,
    compare_agents, get_followup_candidates, search_transcripts,
    get_call_time_analysis, get_conversion_funnel, get_weekly_summary_data
)
from lib.export_report import export_call_quality_report, export_intent_report
from agents.predictions import (
    get_sales_predictions, get_lead_prediction, get_conversion_forecast,
    get_next_best_action, get_action_queue,
    get_site_visit_predictions, get_lead_site_visit_probability
)
from lib.notifications import (
    send_followup_email, send_whatsapp_followup_by_lead,
    bulk_send_whatsapp_to_category
)
from agents.objections import get_objection_keyword_counts, analyze_objection_patterns
app = Server("leadscore-mcp")

from agents.call_analysis import generate_meeting_summary
from lib.db import execute
from lib.chatbot import answer_from_knowledge_base



@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="analyse_calls",
            description="Analyze call quality for multiple transcribed sales calls. Returns quality scores, agent technique, engagement, and coaching recommendations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of calls to analyze (default 5, keep small to avoid timeouts)",
                    },
                    "agent": {
                        "type": "string",
                        "description": "Filter by agent name (optional)",
                    },
                },
            },
        ),
        Tool(
            name="get_call_quality_report",
            description="Get a detailed quality report for a single specific call by its call ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "description": "The call ID to analyze",
                    },
                },
                "required": ["call_id"],
            },
        ),
        Tool(
            name="analyse_intent_sentiment",
            description="Analyze buyer intent and sentiment for multiple sales calls. Returns intent stage (ready_to_buy/researching/not_interested/etc), sentiment progression, and readiness scores.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of calls to analyze (default 5)",
                    },
                },
            },
        ),
        Tool(
            name="get_lead_intent_detail",
            description="Get detailed buyer intent and sentiment analysis for a specific call by call ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "description": "The call ID to analyze",
                    },
                },
                "required": ["call_id"],
            },
        ),
    
        Tool(
            name="get_all_leads",
            description="Get a list of all leads with their scores and Hot/Warm/Cold category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max leads to return (default 50)"},
                },
            },
        ),
        Tool(
            name="get_hot_leads",
            description="Get leads categorized as 'Hot' (highest score, best conversion potential).",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max leads to return (default 20)"},
                },
            },
        ),
        Tool(
            name="get_top_10_leads",
            description="Get the top 10 highest-scoring leads across all agents.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_lead_detail",
            description="Get full score breakdown and call history for one specific lead by lead_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "The lead ID to look up"},
                },
                "required": ["lead_id"],
            },
        ),
        Tool(
            name="get_dashboard_stats",
            description="Get overall dashboard statistics: total leads, calls, hot/warm/cold breakdown, average score.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_agent_performance",
            description="Get call performance stats for a specific agent by name (connect rate, avg score, hot leads generated).",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Agent name to look up"},
                },
                "required": ["agent_name"],
            },
        ),
        Tool(
            name="get_call_analytics",
            description="Get overall call analytics: status breakdown, call type breakdown, transcription rate.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="recommend_leads",
            description="Get recommended leads to follow up with next (Hot + Warm leads, sorted by score).",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of leads to recommend (default 5)"},
                },
            },
        ),
        Tool(
            name="get_saved_call_quality",
            description="Get PRE-ANALYZED call quality results (instant, from database — no AI wait time). Shows top calls by quality score.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
            },
        ),
        Tool(
            name="get_quality_stats_saved",
            description="Get overall call quality statistics from ALL pre-analyzed calls (avg score, success rate, etc). Instant, no AI call needed.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_saved_intent_sentiment",
            description="Get PRE-ANALYZED buyer intent & sentiment results (instant, from database). Shows leads sorted by purchase readiness.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
            },
        ),
        Tool(
            name="get_intent_distribution_saved",
            description="Get breakdown of leads by buyer intent category (ready_to_buy, researching, etc) from pre-analyzed data. Instant.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_agent_quality_ranking",
            description="Get agents ranked by average call quality score, from pre-analyzed data. Instant.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_top_readiness_leads",
            description="Get leads with the highest purchase readiness score, from pre-analyzed sentiment data. Instant.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
            },
        ),
        Tool(
            name="get_lead_full_analysis",
            description="Get ALL saved AI analysis (call quality + buyer intent + sentiment) for a specific lead_id, instantly from database. Use this when asked to 'analyze lead X' or 'show sentiment for lead X'. IMPORTANT: Return ONLY the table data exactly as provided. Do not add summary sentences, opinions, or follow-up questions after the table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "The lead ID to analyze"},
                },
                "required": ["lead_id"],
            },
        ),
        Tool(
            name="get_call_quality_report_table",
            description="Get saved call quality analysis for ONE specific call_id, formatted as a table. Use when asked 'show call quality report for call X'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "call_id": {"type": "string", "description": "The call ID to look up"},
                },
                "required": ["call_id"],
            },
        ),
        Tool(
            name="get_intent_report_table",
            description="Get saved intent/sentiment analysis for ONE specific call_id, formatted as a table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "call_id": {"type": "string", "description": "The call ID to look up"},
                },
                "required": ["call_id"],
            },
        ),
        Tool(
            name="get_agent_leaderboard",
            description="Get a full agent comparison leaderboard table: quality, success rate, and readiness scores side by side for all agents.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_outcome_breakdown",
            description="Get call outcome distribution (successful/partial/unsuccessful) as a table with counts and average quality.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_call_transcript",
            description="Get the RAW transcript text for a specific call_id. Use when asked to 'show the transcript' or 'read the conversation' for a call.",
            inputSchema={
                "type": "object",
                "properties": {
                    "call_id": {"type": "string", "description": "The call ID to look up"},
                },
                "required": ["call_id"],
            },
        ),
        Tool(
            name="compare_agents",
            description="Compare two agents side-by-side: quality, technique, engagement, success rate, readiness. Use when asked to 'compare agent X vs agent Y'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent1": {"type": "string", "description": "First agent name"},
                    "agent2": {"type": "string", "description": "Second agent name"},
                },
                "required": ["agent1", "agent2"],
            },
        ),
        Tool(
            name="get_followup_reminders",
            description="Get leads with high readiness scores that need follow-up. Use when asked 'who should I follow up with' or 'who's going cold'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_readiness": {"type": "integer", "description": "Minimum readiness score (default 50)"},
                    "limit": {"type": "integer", "description": "Max results (default 15)"},
                },
            },
        ),
        Tool(
            name="search_call_transcripts",
            description="Search all call transcripts for a keyword (e.g., 'price', 'competitor', 'not interested'). Returns matching calls with snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Word or phrase to search for"},
                    "limit": {"type": "integer", "description": "Max results (default 15)"},
                },
                "required": ["keyword"],
            },
        ),
        Tool(
            name="get_call_time_analysis",
            description="Analyze call performance by hour of day — shows which hours have the best connect rates. Use for 'best time to call' questions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_conversion_funnel",
            description="Get the lead conversion funnel: Total Leads -> Connected -> Transcribed -> Intent stages. Use for 'show me the funnel' questions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_summary_report",
            description="Get a combined summary report: quality stats, intent distribution, top leads, and agent ranking all together. Use for 'give me a summary/briefing/report'.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="export_data_report",
            description="Export call quality or intent/sentiment data to a CSV file on disk. Use when asked to 'export' or 'download' a report.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_type": {
                        "type": "string",
                        "description": "Which report to export: 'quality' or 'intent'",
                        "enum": ["quality", "intent"],
                    },
                },
                "required": ["report_type"],
            },
        ),
        Tool(
            name="get_sales_predictions",
            description="Get leads ranked by AI-predicted conversion probability. Use for 'which leads will convert' or 'sales prediction' questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 15)"},
                },
            },
        ),
        Tool(
            name="get_lead_conversion_prediction",
            description="Get conversion probability for ONE specific lead_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "The lead ID"},
                },
                "required": ["lead_id"],
            },
        ),
        Tool(
            name="get_revenue_forecast",
            description="Get expected conversion forecast across all leads (count-based, by probability bucket). Use for 'revenue forecast' or 'how many will we close' questions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_next_best_action_for_lead",
            description="Get the AI-recommended next best action for ONE specific lead_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "The lead ID"},
                },
                "required": ["lead_id"],
            },
        ),
        Tool(
            name="get_action_queue",
            description="Get a prioritized list of next-best-actions across ALL leads, sorted by urgency. Use for 'what should I do today' questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 15)"},
                },
            },
        ),
        Tool(
            name="get_site_visit_predictions",
            description="Get leads ranked by predicted likelihood of an in-person site visit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 15)"},
                },
            },
        ),
        Tool(
            name="get_lead_site_visit_probability",
            description="Get site visit probability for ONE specific lead_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "The lead ID"},
                },
                "required": ["lead_id"],
            },
        ),
        Tool(
            name="send_whatsapp_followup",
            description="Send a WhatsApp follow-up message to a lead. Automatically looks up their phone number from the database. Use when asked to 'send WhatsApp to lead X' or 'WhatsApp follow-up for lead X'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "The lead ID to message"},
                },
                "required": ["lead_id"],
            },
        ),
        Tool(
            name="send_email_followup",
            description="Send a follow-up email to a lead. Requires the email address to be provided manually since we don't store emails. Use when asked to 'send email to lead X at [email]'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "The lead ID"},
                    "email_address": {"type": "string", "description": "The email address to send to"},
                },
                "required": ["lead_id", "email_address"],
            },
        ),
        Tool(
            name="bulk_send_whatsapp",
            description="Send WhatsApp follow-ups to ALL leads in a category (Hot/Warm/Cold) at once. Skips leads already contacted in the last 3 days. Use for 'send WhatsApp to all hot leads' type requests.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Lead category: Hot, Warm, or Cold",
                        "enum": ["Hot", "Warm", "Cold"],
                    },
                    "limit": {"type": "integer", "description": "Max leads to message (default 20)"},
                },
                "required": ["category"],
            },
        ),
        Tool(
            name="get_message_history",
            description="Get the history of sent messages (WhatsApp/email) for a specific lead, or recent messages overall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "Optional: filter by lead ID"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
            },
        ),
        Tool(
            name="find_duplicate_leads",
            description="Find phone numbers that appear under multiple different lead_ids (potential duplicates).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_objection_keywords",
            description="Fast count of how many transcripts mention common objection keywords (price, competitor, etc).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="analyze_objection_patterns",
            description="AI-powered analysis of common objection THEMES across a sample of transcripts (uses Gemini, costs tokens).",
            inputSchema={
                "type": "object",
                "properties": {
                    "sample_size": {"type": "integer", "description": "Number of transcripts to sample (default 15)"},
                },
            },
        ),
        Tool(
            name="generate_call_summary",
            description="Generate an AI meeting summary (summary, key points, mood, objections) for a specific call.",
            inputSchema={
                "type": "object",
                "properties": {"call_id": {"type": "string", "description": "Call ID"}},
                "required": ["call_id"],
            },
        ),
        Tool(
            name="ask_company_knowledge",
            description="Answer a sales question using company documents (SOP, pricing, FAQs). Use when asked 'what should I tell the customer about X' or similar policy/pricing questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to answer using company knowledge"},
                },
                "required": ["question"],
            },
        ),
    ]
    


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "analyse_calls":
            limit = min(int(arguments.get("limit") or 5), 15)
            agent = arguments.get("agent")

            sql = "SELECT * FROM calls WHERE transcript_status = 'done'"
            params = []
            if agent:
                sql += " AND agent_name LIKE %s"
                params.append(f"%{agent}%")
            sql += f" ORDER BY call_date DESC LIMIT {limit}"

            calls = query(sql, params)

            if not calls:
                return [TextContent(type="text", text="No transcribed calls found matching those filters.")]

            result = analyze_call_batch(calls)

            lines = [f"AI Call Quality Analysis", "-" * 50]
            lines.append(f"Calls analyzed: {len(calls)}")
            lines.append(f"Average quality: {result['summary']['average_quality_score']}/100")
            lines.append(f"Success rate: {result['summary']['success_rate']*100:.1f}%\n")

            for c in result["calls"]:
                lines.append(f"Call {c['call_number']}: Quality={c['quality_score']}/100, Outcome={c['call_outcome']}")
                lines.append(f"  Recommendation: {c['recommendation']}\n")

            lines.append(f"Team Pattern: {result['summary']['team_pattern']}")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_call_quality_report":
            call_id = arguments["call_id"]
            calls = query("SELECT * FROM calls WHERE id = %s", [call_id])

            if not calls:
                return [TextContent(type="text", text=f"Call {call_id} not found.")]

            result = analyze_single_call(calls[0])

            lines = [
                f"Call Quality Report — Call #{call_id}",
                "-" * 50,
                f"Quality Score: {result['quality_score']}/100",
                f"Agent Technique: {result['agent_technique']}/10",
                f"Engagement: {result['engagement_quality']}/10",
                f"Outcome: {result['call_outcome']} — {result['outcome_reason']}",
                "",
                "Strengths:",
            ]
            lines += [f"  - {s}" for s in result["strengths"]]
            lines.append("\nImprovements:")
            lines += [f"  - {i}" for i in result["improvements"]]
            lines.append(f"\nTop Recommendation: {result['top_recommendation']}")
            lines.append(f"Next Action: {result['next_action']}")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "analyse_intent_sentiment":
            limit = min(int(arguments.get("limit") or 5), 15)
            calls = query(
                f"SELECT * FROM calls WHERE transcript_status = 'done' ORDER BY call_date DESC LIMIT {limit}"
            )

            if not calls:
                return [TextContent(type="text", text="No transcribed calls found.")]

            result = analyze_intent_sentiment_batch(calls)

            lines = [f"AI Intent & Sentiment Analysis", "-" * 50]
            lines.append(f"Calls analyzed: {len(calls)}")
            lines.append(f"Intent distribution: {json.dumps(result['summary']['intent_distribution'])}")
            lines.append(f"Avg readiness: {result['summary']['avg_readiness_score']}/100\n")

            for c in result["calls"]:
                lines.append(f"Call {c['call_number']}: Intent={c['buyer_intent']}, Readiness={c['readiness_score']}/100")
                lines.append(f"  Sentiment: {c['initial_sentiment']} -> {c['final_sentiment']} | Engagement: {c['engagement_level']}")
                lines.append(f"  {c['key_reason']}\n")

            lines.append(f"Insight: {result['summary']['insight']}")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_lead_intent_detail":
            call_id = arguments["call_id"]
            calls = query("SELECT * FROM calls WHERE id = %s", [call_id])

            if not calls:
                return [TextContent(type="text", text=f"Call {call_id} not found.")]

            result = analyze_single_call_intent(calls[0])

            lines = [
                f"Intent & Sentiment Detail — Call #{call_id}",
                "-" * 50,
                f"Buyer Intent: {result['buyer_intent']}",
                f"Reasoning: {result['intent_reasoning']}",
                f"Sentiment: {result['initial_sentiment']} -> {result['final_sentiment']}",
                f"Shift Reason: {result['sentiment_shift_reason']}",
                f"Engagement: {result['engagement_level']}",
                f"Readiness Score: {result['readiness_score']}/100",
                "",
                "Positive Signals:",
            ]
            lines += [f"  - {s}" for s in result["positive_signals"]] or ["  (none)"]
            lines.append("\nNegative Signals:")
            lines += [f"  - {s}" for s in result["negative_signals"]] or ["  (none)"]
            lines.append(f"\nRecommended Next Action: {result['recommended_next_action']}")

            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "get_all_leads":
            limit = min(int(arguments.get("limit") or 50), 100)
            leads = get_all_leads(limit)
            lines = [f"All Leads (showing {len(leads)})", "-" * 50]
            for l in leads:
                lines.append(f"Lead {l['lead_id']}: Score={l['score']} ({l['category']}) - {l['agent_name']} - {l['status']}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_hot_leads":
            limit = min(int(arguments.get("limit") or 20), 50)
            leads = get_hot_leads(limit)
            lines = [f"Hot Leads (showing {len(leads)})", "-" * 50]
            for l in leads:
                lines.append(f"Lead {l['lead_id']}: Score={l['score']} - {l['agent_name']} - {l['status']} - {l['call_date']}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_top_10_leads":
            leads = get_top_10_leads()
            lines = ["Top 10 Leads", "-" * 50]
            for i, l in enumerate(leads, 1):
                lines.append(f"{i}. Lead {l['lead_id']}: Score={l['score']} ({l['category']}) - {l['agent_name']}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_lead_detail":
            detail = get_lead_detail(arguments["lead_id"])
            if not detail:
                return [TextContent(type="text", text=f"Lead {arguments['lead_id']} not found.")]
            lines = [
                f"Lead {detail['lead_id']} Detail",
                "-" * 50,
                f"Best Score: {detail['best_score']} ({detail['best_category']})",
                f"Agent: {detail['agent_name']}",
                f"Total calls: {detail['total_calls']}",
                "",
                "Call History:",
            ]
            for c in detail["call_history"]:
                lines.append(f"  Call {c['call_id']}: {c['status']} | {c['duration_sec']}s | Score={c['score']} ({c['category']}) | Transcript={'Yes' if c['has_transcript'] else 'No'}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_dashboard_stats":
            stats = get_dashboard_stats()
            lines = [
                "Dashboard Stats",
                "-" * 50,
                f"Total Leads: {stats['total_leads']}",
                f"Transcribed Calls: {stats['transcribed_calls']}",
                f"Hot Leads: {stats['hot_leads']}",
                f"Warm Leads: {stats['warm_leads']}",
                f"Cold Leads: {stats['cold_leads']}",
                f"Average Score: {stats['avg_score']}",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_agent_performance":
            perf = get_agent_performance(arguments["agent_name"])
            if not perf:
                return [TextContent(type="text", text=f"No calls found for agent '{arguments['agent_name']}'.")]
            lines = [
                f"Agent Performance — {perf['agent_name']}",
                "-" * 50,
                f"Total Calls: {perf['total_calls']}",
                f"Completed Calls: {perf['completed_calls']}",
                f"Connect Rate: {perf['connect_rate']*100:.1f}%",
                f"Unique Leads: {perf['unique_leads']}",
                f"Transcribed Calls: {perf['transcribed_calls']}",
                f"Average Score: {perf['avg_score']}",
                f"Hot Leads Generated: {perf['hot_leads_generated']}",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_call_analytics":
            analytics = get_call_analytics()
            lines = [
                "Call Analytics",
                "-" * 50,
                f"Total Calls: {analytics['total_calls']}",
                f"Status Breakdown: {json.dumps(analytics['status_breakdown'])}",
                f"Call Type Breakdown: {json.dumps(analytics['call_type_breakdown'])}",
                f"Average Score: {analytics['avg_score']}",
                f"Transcription Rate: {analytics['transcription_rate']}%",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "recommend_leads":
            count = min(int(arguments.get("count") or 5), 20)
            leads = recommend_leads(count)
            lines = [f"Recommended Leads to Follow Up ({len(leads)})", "-" * 50]
            for l in leads:
                lines.append(f"Lead {l['lead_id']}: Score={l['score']} ({l['category']}) - {l['agent_name']} - {l['status']}")
            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "get_saved_call_quality":
            limit = min(int(arguments.get("limit") or 10), 50)
            rows = get_call_quality_summary(limit)
            lines = [f"Saved Call Quality Results (Top {len(rows)})", "-" * 50]
            for r in rows:
                lines.append(f"Call {r['call_id']} | Lead {r['lead_id']} | {r['agent_name']}: Quality={r['quality_score']}/100, Outcome={r['call_outcome']}")
                lines.append(f"  Recommendation: {r['recommendation']}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_quality_stats_saved":
            stats = get_quality_stats()
            lines = [
                "Overall Call Quality Statistics (from all analyzed calls)",
                "-" * 50,
                f"Total Analyzed: {stats['total_analyzed']}",
                f"Average Quality: {stats['avg_quality']}/100",
                f"Average Technique: {stats['avg_technique']}/10",
                f"Average Engagement: {stats['avg_engagement']}/10",
                f"Successful: {stats['successful']}",
                f"Partial: {stats['partial']}",
                f"Unsuccessful: {stats['unsuccessful']}",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_saved_intent_sentiment":
            limit = min(int(arguments.get("limit") or 10), 50)
            rows = get_intent_summary(limit)
            lines = [f"Saved Intent & Sentiment Results (Top {len(rows)} by readiness)", "-" * 50]
            for r in rows:
                lines.append(f"Call {r['call_id']} | Lead {r['lead_id']}: Intent={r['buyer_intent']}, Readiness={r['readiness_score']}/100")
                lines.append(f"  Sentiment: {r['initial_sentiment']} -> {r['final_sentiment']} | Engagement: {r['engagement_level']}")
                lines.append(f"  {r['key_reason']}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_intent_distribution_saved":
            rows = get_intent_distribution()
            lines = ["Intent Distribution (from pre-analyzed data)", "-" * 50]
            for r in rows:
                lines.append(f"{r['buyer_intent']}: {r['count']} leads (avg readiness: {r['avg_readiness']})")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_agent_quality_ranking":
            rows = get_agent_quality_ranking()
            lines = ["Agent Quality Ranking (from pre-analyzed data)", "-" * 50]
            for r in rows:
                lines.append(f"{r['agent_name']}: {r['avg_quality']}/100 avg ({r['calls_analyzed']} calls, {r['successful_calls']} successful)")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_top_readiness_leads":
            limit = min(int(arguments.get("limit") or 10), 50)
            rows = get_top_readiness_leads(limit)
            lines = [f"Top Leads by Purchase Readiness (Top {len(rows)})", "-" * 50]
            for r in rows:
                lines.append(f"Lead {r['lead_id']} | Call {r['call_id']} | {r['agent_name']}: Readiness={r['readiness_score']}/100, Intent={r['buyer_intent']}")
                lines.append(f"  {r['key_reason']}")
            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "get_lead_full_analysis":
            result = get_lead_full_analysis(arguments["lead_id"])
            if not result:
                return [TextContent(type="text", text=f"No saved analysis found for lead {arguments['lead_id']}. It may not have a transcript yet.")]

            lines = [f"### Lead {result['lead_id']} — Call Analysis\n"]
            lines.append("| Call ID | Date | Agent | Quality | Outcome | Intent | Readiness | Sentiment |")
            lines.append("|---|---|---|---|---|---|---|---|")

            for c in result["calls"]:
                call_id = c["call_id"]
                date = str(c["call_date"])[:10] if c["call_date"] else "N/A"
                agent = c["agent_name"] or "N/A"
                quality = f"{c['quality_score']}/100" if c["quality_score"] is not None else "N/A"
                outcome = c["call_outcome"] or "N/A"
                intent = c["buyer_intent"] or "N/A"
                readiness = f"{c['readiness_score']}/100" if c["readiness_score"] is not None else "N/A"
                sentiment = f"{c['initial_sentiment']}->{c['final_sentiment']}" if c["initial_sentiment"] else "N/A"

                lines.append(f"| {call_id} | {date} | {agent} | {quality} | {outcome} | {intent} | {readiness} | {sentiment} |")

            # Add recommendations below the table (only non-empty ones)
            recs = [f"- Call {c['call_id']}: {c['recommendation']}" for c in result["calls"] if c.get("recommendation")]
            if recs:
                lines.append("\n**Recommendations:**")
                lines.extend(recs)

            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "get_call_quality_report_table":
            r = get_call_quality_by_id(arguments["call_id"])
            if not r:
                return [TextContent(type="text", text=f"No saved quality analysis for call {arguments['call_id']}.")]
            lines = [
                f"### Call {r['call_id']} — Quality Report\n",
                "| Field | Value |",
                "|---|---|",
                f"| Lead ID | {r['lead_id']} |",
                f"| Agent | {r['agent_name']} |",
                f"| Date | {str(r['call_date'])[:10] if r['call_date'] else 'N/A'} |",
                f"| Duration | {r['call_duration_sec']}s |",
                f"| Quality Score | {r['quality_score']}/100 |",
                f"| Agent Technique | {r['agent_technique']}/10 |",
                f"| Engagement | {r['engagement_quality']}/10 |",
                f"| Outcome | {r['call_outcome']} |",
                f"| Strengths | {r['strengths']} |",
                f"| Improvements | {r['areas_for_improvement']} |",
                f"| Recommendation | {r['recommendation']} |",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_intent_report_table":
            r = get_intent_by_call_id(arguments["call_id"])
            if not r:
                return [TextContent(type="text", text=f"No saved intent analysis for call {arguments['call_id']}.")]
            lines = [
                f"### Call {r['call_id']} — Intent & Sentiment Report\n",
                "| Field | Value |",
                "|---|---|",
                f"| Lead ID | {r['lead_id']} |",
                f"| Buyer Intent | {r['buyer_intent']} |",
                f"| Initial Sentiment | {r['initial_sentiment']} |",
                f"| Final Sentiment | {r['final_sentiment']} |",
                f"| Engagement Level | {r['engagement_level']} |",
                f"| Readiness Score | {r['readiness_score']}/100 |",
                f"| Key Reason | {r['key_reason']} |",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_agent_leaderboard":
            rows = get_agent_leaderboard_table()
            lines = ["### Agent Leaderboard\n"]
            lines.append("| Agent | Total Calls | Avg Quality | Successful | Avg Readiness |")
            lines.append("|---|---|---|---|---|")
            for r in rows:
                lines.append(f"| {r['agent_name'] or 'N/A'} | {r['total_calls']} | {r['avg_quality'] or 'N/A'} | {r['successful_calls'] or 0} | {r['avg_readiness'] or 'N/A'} |")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_outcome_breakdown":
            rows = get_outcome_breakdown_table()
            lines = ["### Call Outcome Breakdown\n"]
            lines.append("| Outcome | Call Count | Avg Quality |")
            lines.append("|---|---|---|")
            for r in rows:
                lines.append(f"| {r['call_outcome']} | {r['call_count']} | {r['avg_quality']} |")
            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "get_call_transcript":
            r = get_call_transcript(arguments["call_id"])
            if not r:
                return [TextContent(type="text", text=f"Call {arguments['call_id']} not found.")]
            if r["transcript_status"] != "done" or not r["transcript"]:
                return [TextContent(type="text", text=f"Call {r['id']} has no transcript available.")]

            lines = [
                f"### Transcript — Call {r['id']}\n",
                f"**Lead ID:** {r['lead_id']} | **Agent:** {r['agent_name']} | **Date:** {str(r['call_date'])[:10] if r['call_date'] else 'N/A'} | **Duration:** {r['call_duration_sec']}s\n",
                "---\n",
                r["transcript"],
            ]
            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "compare_agents":
            result = compare_agents(arguments["agent1"], arguments["agent2"])
            s1, s2 = result["agent1_stats"], result["agent2_stats"]

            lines = [f"### Agent Comparison: {result['agent1_name']} vs {result['agent2_name']}\n"]
            lines.append("| Metric | " + result["agent1_name"] + " | " + result["agent2_name"] + " |")
            lines.append("|---|---|---|")
            if s1 and s2:
                lines.append(f"| Total Calls | {s1['total_calls']} | {s2['total_calls']} |")
                lines.append(f"| Avg Quality | {s1['avg_quality']} | {s2['avg_quality']} |")
                lines.append(f"| Avg Technique | {s1['avg_technique']} | {s2['avg_technique']} |")
                lines.append(f"| Avg Engagement | {s1['avg_engagement']} | {s2['avg_engagement']} |")
                lines.append(f"| Successful Calls | {s1['successful']} | {s2['successful']} |")
                lines.append(f"| Avg Readiness | {s1['avg_readiness']} | {s2['avg_readiness']} |")
            else:
                lines.append("| No data found for one or both agents | - | - |")

            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "get_followup_reminders":
            min_readiness = int(arguments.get("min_readiness") or 50)
            limit = min(int(arguments.get("limit") or 15), 30)
            rows = get_followup_candidates(min_readiness, limit)

            lines = ["### Follow-Up Reminders (High Readiness Leads)\n"]
            lines.append("| Lead ID | Call ID | Agent | Intent | Readiness | Days Since Call |")
            lines.append("|---|---|---|---|---|---|")
            for r in rows:
                lines.append(f"| {r['lead_id']} | {r['call_id']} | {r['agent_name'] or 'N/A'} | {r['buyer_intent']} | {r['readiness_score']}/100 | {r['days_since_call']} |")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "search_call_transcripts":
            keyword = arguments["keyword"]
            limit = min(int(arguments.get("limit") or 15), 30)
            rows = search_transcripts(keyword, limit)

            if not rows:
                return [TextContent(type="text", text=f"No transcripts found containing '{keyword}'.")]

            lines = [f"### Transcript Search: \"{keyword}\" ({len(rows)} matches)\n"]
            lines.append("| Call ID | Lead ID | Agent | Snippet |")
            lines.append("|---|---|---|---|")
            for r in rows:
                snippet = r["snippet"].replace("|", "-").replace("\n", " ")
                lines.append(f"| {r['call_id']} | {r['lead_id']} | {r['agent_name'] or 'N/A'} | {snippet} |")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_call_time_analysis":
            rows = get_call_time_analysis()

            lines = ["### Call Performance by Hour\n"]
            lines.append("| Hour | Total Calls | Connected | Connect Rate | Avg Duration |")
            lines.append("|---|---|---|---|---|")
            for r in rows:
                rate = f"{(r['connected']/r['total_calls']*100):.0f}%" if r['total_calls'] else "0%"
                lines.append(f"| {r['call_hour']}:00 | {r['total_calls']} | {r['connected']} | {rate} | {r['avg_duration']}s |")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_conversion_funnel":
            f = get_conversion_funnel()

            lines = ["### Lead Conversion Funnel\n"]
            lines.append("| Stage | Count |")
            lines.append("|---|---|")
            lines.append(f"| Total Leads | {f['total_leads']} |")
            lines.append(f"| Connected | {f['connected']} |")
            lines.append(f"| Transcribed | {f['transcribed']} |")
            lines.append(f"| Ready to Buy | {f['ready_to_buy']} |")
            lines.append(f"| Actively Considering | {f['actively_considering']} |")
            lines.append(f"| Researching | {f['researching']} |")
            lines.append(f"| Skeptical | {f['skeptical']} |")
            lines.append(f"| Not Interested | {f['not_interested']} |")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_summary_report":
            data = get_weekly_summary_data()
            q = data["quality_stats"]

            lines = ["### Summary Report\n"]
            lines.append("**Call Quality**")
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            lines.append(f"| Total Analyzed | {q['total_analyzed']} |")
            lines.append(f"| Avg Quality | {q['avg_quality']}/100 |")
            lines.append(f"| Successful | {q['successful']} |")
            lines.append(f"| Partial | {q['partial']} |")
            lines.append(f"| Unsuccessful | {q['unsuccessful']} |")

            lines.append("\n**Intent Distribution**")
            lines.append("| Intent | Count | Avg Readiness |")
            lines.append("|---|---|---|")
            for i in data["intent_distribution"]:
                lines.append(f"| {i['buyer_intent']} | {i['count']} | {i['avg_readiness']} |")

            lines.append("\n**Top 5 Readiness Leads**")
            lines.append("| Lead ID | Call ID | Readiness | Intent |")
            lines.append("|---|---|---|---|")
            for t in data["top_leads"]:
                lines.append(f"| {t['lead_id']} | {t['call_id']} | {t['readiness_score']}/100 | {t['buyer_intent']} |")

            lines.append("\n**Agent Ranking**")
            lines.append("| Agent | Avg Quality | Calls | Successful |")
            lines.append("|---|---|---|---|")
            for a in data["agent_ranking"]:
                lines.append(f"| {a['agent_name'] or 'N/A'} | {a['avg_quality']} | {a['calls_analyzed']} | {a['successful_calls']} |")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "export_data_report":
            report_type = arguments["report_type"]
            if report_type == "quality":
                filepath, count = export_call_quality_report()
            else:
                filepath, count = export_intent_report()

            return [TextContent(type="text", text=f"Exported {count} records to:\n{filepath}")]
        
        if name == "get_sales_predictions":
            limit = min(int(arguments.get("limit") or 15), 30)
            rows = get_sales_predictions(limit)
            lines = ["### Sales Predictions\n"]
            lines.append("| Lead ID | Call ID | Agent | Probability | Intent |")
            lines.append("|---|---|---|---|---|")
            for r in rows:
                lines.append(f"| {r['lead_id']} | {r['call_id']} | {r['agent_name'] or 'N/A'} | {r['conversion_probability']}% | {r['buyer_intent']} |")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_lead_conversion_prediction":
            r = get_lead_prediction(arguments["lead_id"])
            if not r:
                return [TextContent(type="text", text=f"No prediction data for lead {arguments['lead_id']}.")]
            lines = [
                f"### Conversion Prediction — Lead {r['lead_id']}\n",
                "| Field | Value |",
                "|---|---|",
                f"| Conversion Probability | {r['conversion_probability']}% |",
                f"| Buyer Intent | {r['buyer_intent']} |",
                f"| Quality Score | {r['quality_score']} |",
                f"| Readiness Score | {r['readiness_score']} |",
                f"| Sentiment | {r['sentiment']} |",
                f"| Engagement | {r['engagement']} |",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_revenue_forecast":
            f = get_conversion_forecast()
            lines = [
                "### Conversion Forecast\n",
                "| Metric | Value |",
                "|---|---|",
                f"| Total Leads Analyzed | {f['total_leads_analyzed']} |",
                f"| Expected Conversions | {f['expected_conversions']} |",
                f"| Very Likely (75%+) | {f['very_likely_count']} |",
                f"| Likely (50-74%) | {f['likely_count']} |",
                f"| Possible (25-49%) | {f['possible_count']} |",
                f"| Unlikely (<25%) | {f['unlikely_count']} |",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_next_best_action_for_lead":
            r = get_next_best_action(arguments["lead_id"])
            if not r:
                return [TextContent(type="text", text=f"No action data for lead {arguments['lead_id']}.")]
            lines = [
                f"### Next Best Action — Lead {r['lead_id']}\n",
                "| Field | Value |",
                "|---|---|",
                f"| Priority | {r['priority']} |",
                f"| Recommended Action | {r['recommended_action']} |",
                f"| Conversion Probability | {r['conversion_probability']}% |",
                f"| Buyer Intent | {r['buyer_intent']} |",
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_action_queue":
            limit = min(int(arguments.get("limit") or 15), 30)
            rows = get_action_queue(limit)
            lines = ["### Action Queue (Prioritized)\n"]
            lines.append("| Priority | Lead ID | Probability | Recommended Action |")
            lines.append("|---|---|---|---|")
            for r in rows:
                lines.append(f"| {r['priority']} | {r['lead_id']} | {r['conversion_probability']}% | {r['recommended_action']} |")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_site_visit_predictions":
            limit = min(int(arguments.get("limit") or 15), 30)
            rows = get_site_visit_predictions(limit)
            lines = ["### Site Visit Predictions\n"]
            lines.append("| Lead ID | Call ID | Agent | Visit Probability | Intent |")
            lines.append("|---|---|---|---|---|")
            for r in rows:
                lines.append(f"| {r['lead_id']} | {r['call_id']} | {r['agent_name'] or 'N/A'} | {r['site_visit_probability']}% | {r['buyer_intent']} |")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_lead_site_visit_probability":
            r = get_lead_site_visit_probability(arguments["lead_id"])
            if not r:
                return [TextContent(type="text", text=f"No site visit data for lead {arguments['lead_id']}.")]
            lines = [
                f"### Site Visit Probability — Lead {r['lead_id']}\n",
                "| Field | Value |",
                "|---|---|",
                f"| Visit Probability | {r['site_visit_probability']}% |",
                f"| Buyer Intent | {r['buyer_intent']} |",
                f"| Engagement | {r['engagement']} |",
            ]
            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "send_whatsapp_followup":
            success, msg = send_whatsapp_followup_by_lead(arguments["lead_id"])
            status = "Sent" if success else "Failed"
            return [TextContent(type="text", text=f"WhatsApp Follow-up — {status}\n{msg}")]

        if name == "send_email_followup":
            success, msg = send_followup_email(arguments["lead_id"], arguments["email_address"])
            status = "Sent" if success else "Failed"
            return [TextContent(type="text", text=f"Email Follow-up — {status}\n{msg}")]
        
        if name == "bulk_send_whatsapp":
            category = arguments["category"]
            limit = min(int(arguments.get("limit") or 20), 50)
            result = bulk_send_whatsapp_to_category(category, limit)

            lines = [f"### Bulk WhatsApp Campaign — {category} Leads\n"]
            lines.append(f"Sent: {result['sent']} | Skipped (recent contact): {result['skipped']} | Failed: {result['failed']}\n")
            lines.append("| Lead ID | Status | Detail |")
            lines.append("|---|---|---|")
            for d in result["details"]:
                status = "Sent" if d["success"] else "Skipped/Failed"
                lines.append(f"| {d['lead_id']} | {status} | {d['message']} |")

            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_message_history":
            sql = "SELECT * FROM message_log"
            params = []
            if arguments.get("lead_id"):
                sql += " WHERE lead_id = %s"
                params.append(arguments["lead_id"])
            sql += " ORDER BY sent_at DESC LIMIT %s"
            params.append(min(int(arguments.get("limit") or 20), 50))

            rows = query(sql, params)

            lines = ["### Message History\n"]
            lines.append("| Lead ID | Channel | Recipient | Status | Sent At |")
            lines.append("|---|---|---|---|---|")
            for r in rows:
                lines.append(f"| {r['lead_id']} | {r['channel']} | {r['recipient']} | {r['status']} | {r['sent_at']} |")

            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "find_duplicate_leads":
            rows = find_duplicate_phone_numbers()
            lines = ["Duplicate Phone Numbers", "-" * 50]
            for r in rows:
                lines.append(f"Phone {r['phone_number']}: {r['lead_count']} leads -> {r['lead_ids']}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "get_objection_keywords":
            result = get_objection_keyword_counts()
            lines = ["Objection Keyword Counts", "-" * 50, f"Total transcripts: {result['total_transcripts']}", ""]
            for kw, count in result["keyword_counts"].items():
                lines.append(f"  '{kw}': {count} mentions")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "analyze_objection_patterns":
            sample_size = min(int(arguments.get("sample_size") or 15), 30)
            result = analyze_objection_patterns(sample_size)
            lines = ["AI Objection Pattern Analysis", "-" * 50]
            for t in result.get("themes", []):
                lines.append(f"  {t['objection']} (frequency: {t['frequency']})")
                lines.append(f"    Example: {t['example_quote']}")
            lines.append(f"\nSummary: {result.get('summary', '')}")
            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "generate_call_summary":
            calls = query("SELECT * FROM calls WHERE id = %s", [arguments["call_id"]])
            if not calls:
                return [TextContent(type="text", text="Call not found.")]
            result = generate_meeting_summary(calls[0])
            execute(
                """INSERT INTO call_summaries (call_id, summary, key_points, customer_mood, objections)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE summary=VALUES(summary), key_points=VALUES(key_points),
                customer_mood=VALUES(customer_mood), objections=VALUES(objections)""",
                [arguments["call_id"], result["summary"], ", ".join(result["key_points"]),
                 result["customer_mood"], ", ".join(result["objections"])],
            )
            lines = [
                f"Call Summary — {arguments['call_id']}", "-" * 40,
                f"Summary: {result['summary']}",
                f"Key Points: {', '.join(result['key_points'])}",
                f"Mood: {result['customer_mood']}",
                f"Objections: {', '.join(result['objections'])}",
            ]
            return [TextContent(type="text", text="\n".join(lines))]
        
        if name == "ask_company_knowledge":
            result = answer_from_knowledge_base(arguments["question"])
            lines = [result["answer"]]
            if result["sources"]:
                lines.append(f"\n(Source: {', '.join(result['sources'])})")
            return [TextContent(type="text", text="\n".join(lines))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    try:
        total = query("SELECT COUNT(*) as c FROM calls")[0]["c"]
        transcribed = query("SELECT COUNT(*) as c FROM calls WHERE transcript_status = 'done'")[0]["c"]
        print(f"Connected to MySQL — {total} calls, {transcribed} transcribed", file=sys.stderr)
    except Exception as e:
        print(f"DB connection warning: {e}", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())