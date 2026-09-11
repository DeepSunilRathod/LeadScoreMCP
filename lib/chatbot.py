"""
lib/chatbot.py — Embedded AI chatbot for the web dashboard.
Uses Gemini to route a natural-language question to the right saved-data
function, then formats a natural-language answer from real results.

SAFETY: Read-only. Does not send WhatsApp/email — those stay as explicit UI buttons.
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.gemini import call_gemini_json, call_gemini
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
    get_call_time_analysis, get_conversion_funnel
)
from agents.predictions import (
    get_sales_predictions, get_lead_prediction, get_conversion_forecast,
    get_next_best_action, get_action_queue,
    get_site_visit_predictions, get_lead_site_visit_probability
)
from lib.db import query as db_query


# ============================================================
# TOOL REGISTRY — name -> (function, description, needs_arg)
# ============================================================

TOOLS = {
    "get_dashboard_stats": (lambda args: get_dashboard_stats(), "Overall dashboard stats: total/hot/warm/cold leads"),
    "get_hot_leads": (lambda args: get_hot_leads(10), "List of hot leads"),
    "get_top_10_leads": (lambda args: get_top_10_leads(), "Top 10 highest scoring leads"),
    "get_lead_detail": (lambda args: get_lead_detail(args.get("lead_id")), "Detail + call history for one lead_id"),
    "get_lead_full_analysis": (lambda args: get_lead_full_analysis(args.get("lead_id")), "AI analysis (quality+intent) for one lead_id"),
    "get_agent_performance": (lambda args: get_agent_performance(args.get("agent_name", "")), "Performance stats for one agent"),
    "get_agent_leaderboard_table": (lambda args: get_agent_leaderboard_table(), "All agents ranked by quality"),
    "compare_agents": (lambda args: compare_agents(args.get("agent1", ""), args.get("agent2", "")), "Compare two agents by name"),
    "get_quality_stats": (lambda args: get_quality_stats(), "Overall call quality statistics"),
    "get_call_quality_by_id": (lambda args: get_call_quality_by_id(args.get("call_id")), "Quality report for one call_id"),
    "get_intent_distribution": (lambda args: get_intent_distribution(), "Buyer intent category breakdown"),
    "get_intent_by_call_id": (lambda args: get_intent_by_call_id(args.get("call_id")), "Intent/sentiment for one call_id"),
    "get_top_readiness_leads": (lambda args: get_top_readiness_leads(10), "Leads with highest purchase readiness"),
    "get_outcome_breakdown_table": (lambda args: get_outcome_breakdown_table(), "Call outcome distribution"),
    "get_sales_predictions": (lambda args: get_sales_predictions(10), "AI sales conversion predictions"),
    "get_lead_prediction": (lambda args: get_lead_prediction(args.get("lead_id")), "Conversion probability for one lead"),
    "get_conversion_forecast": (lambda args: get_conversion_forecast(), "Overall conversion forecast"),
    "get_action_queue": (lambda args: get_action_queue(10), "Prioritized next-best-action list"),
    "get_next_best_action": (lambda args: get_next_best_action(args.get("lead_id")), "Next best action for one lead"),
    "get_site_visit_predictions": (lambda args: get_site_visit_predictions(10), "Site visit probability rankings"),
    "get_followup_candidates": (lambda args: get_followup_candidates(50, 15), "Leads needing follow-up"),
    "search_transcripts": (lambda args: search_transcripts(args.get("keyword", ""), 10), "Search transcripts for a keyword"),
    "get_call_time_analysis": (lambda args: get_call_time_analysis(), "Call performance by hour of day"),
    "get_conversion_funnel": (lambda args: get_conversion_funnel(), "Lead conversion funnel stages"),
    "recommend_leads": (lambda args: recommend_leads(5), "Recommended leads to follow up with"),
}

TOOL_DESCRIPTIONS = "\n".join([f"- {name}: {desc}" for name, (fn, desc) in TOOLS.items()])


def _route_question(question):
    """Ask Gemini which tool fits this question, and extract any needed arguments."""
    prompt = f"""You are a routing engine for a CRM chatbot. Given a user's question,
pick the SINGLE best matching tool from this list:

{TOOL_DESCRIPTIONS}

User question: "{question}"

Extract any arguments needed (lead_id, call_id, agent_name, agent1, agent2, keyword) 
from the question if present.

Return ONLY valid JSON:
{{
  "tool": "tool_name_here",
  "args": {{}}
}}

If no tool clearly matches, return {{"tool": "none", "args": {{}}}}"""

    return call_gemini_json(prompt, max_tokens=1000)


def _format_answer(question, tool_name, result):
    """Ask Gemini to turn raw data + the question into a clean natural-language answer."""
    result_json = json.dumps(result, default=str)[:4000]  # cap size

    prompt = f"""You are a CRM assistant. The user asked: "{question}"

You ran the tool "{tool_name}" and got this data:
{result_json}

Write a concise, helpful answer using ONLY this data. Use a markdown table if 
the data has multiple rows. Do not add unrelated commentary or ask follow-up 
questions. Keep it factual and data-first."""

    return call_gemini(prompt, max_tokens=1000, temperature=0.2)

def search_knowledge_base(query_text, limit=4):
    """
    Simple keyword-based retrieval: find chunks that share the most
    words with the query. Good enough for a small document set.
    """
    words = [w.lower() for w in query_text.split() if len(w) > 3]
    if not words:
        return []

    all_chunks = db_query("SELECT source_file, chunk_text FROM knowledge_base")

    scored = []
    for chunk in all_chunks:
        text_lower = chunk["chunk_text"].lower()
        score = sum(1 for w in words if w in text_lower)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


def answer_from_knowledge_base(question):
    """
    RAG: retrieve relevant company document chunks, then ask Gemini
    to answer using ONLY that context.
    """
    chunks = search_knowledge_base(question)

    if not chunks:
        return {
            "answer": "I couldn't find anything relevant in our company documents for that question.",
            "sources": [],
        }

    context = "\n\n---\n\n".join([f"[From {c['source_file']}]\n{c['chunk_text']}" for c in chunks])

    prompt = f"""You are a sales assistant. Answer the salesperson's question using ONLY 
the company knowledge provided below. If the answer isn't in the provided context, 
say so clearly rather than guessing.

COMPANY KNOWLEDGE:
{context}

QUESTION: {question}

Provide a direct, practical answer a salesperson could use immediately on a call."""

    answer = call_gemini(prompt, max_tokens=600, temperature=0.2)

    sources = list(set(c["source_file"] for c in chunks))
    return {"answer": answer, "sources": sources}

def answer_question(question):
    """
    Main entry point: takes a user question, routes it to a tool,
    executes it, and returns a formatted natural-language answer.
    """
    try:
        routing = _route_question(question)
        tool_name = routing.get("tool", "none")
        args = routing.get("args", {})

        if tool_name == "none" or tool_name not in TOOLS:
            return {
                "answer": "I can only answer questions about leads, calls, agent performance, predictions, and CRM analytics. Please rephrase your question around those topics.",
                "tool_used": None,
            }

        fn, _ = TOOLS[tool_name]
        result = fn(args)

        if result is None:
            return {
                "answer": f"No data found for that request (tool: {tool_name}).",
                "tool_used": tool_name,
            }

        answer_text = _format_answer(question, tool_name, result)
        return {"answer": answer_text, "tool_used": tool_name}

    except Exception as e:
        return {"answer": f"Sorry, something went wrong: {str(e)}", "tool_used": None}


if __name__ == "__main__":
    print("Testing chatbot...")
    r = answer_question("Show me the top 5 hottest leads")
    print(r["answer"])