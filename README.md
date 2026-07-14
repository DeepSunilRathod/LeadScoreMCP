\# LeadScoreMCP — AI-Powered Sales CRM \& Predictive Intelligence Platform



An end-to-end AI CRM system that scores, analyzes, and prioritizes sales leads using

Google Gemini AI, with a full web dashboard, Claude Desktop (MCP) integration,

and automated WhatsApp/Email follow-ups.



\## Features

\- Rule-based lead scoring (Hot/Warm/Cold)

\- AI Call Quality Analysis (multi-language: Hindi, English, Telugu)

\- AI Intent \& Sentiment Analysis

\- Sales Prediction, Revenue Forecast, Next-Best-Action, Site Visit Probability agents

\- Objection pattern detection

\- WhatsApp (Twilio) + Email (Gmail SMTP) automated follow-ups

\- Full enterprise web dashboard (Flask + Chart.js) with role-based access

\- Embedded AI chatbot

\- Model Context Protocol (MCP) server — 25+ tools for Claude Desktop

\- Manager analytics dashboard

\- AI meeting summaries per call



\## Tech Stack

Python · Flask · MySQL · Google Gemini AI · MCP · Twilio · Chart.js · Waitress



\## Setup



1\. Clone the repo

2\. `pip install -r requirements.txt`

3\. Copy `.env.example` to `.env` and fill in your real credentials

4\. Set up MySQL database (`leads\_db`) — schema created automatically on first run

5\. Run: `python web\_app.py` (development) or `python run\_production.py` (production)

6\. Default login: `admin` / `admin123` (created via `python lib/auth.py`)



\## Docker



```bash

docker compose up

```



\## MCP Server (Claude Desktop Integration)



Add to `claude\_desktop\_config.json`:

```json

{

&#x20; "mcpServers": {

&#x20;   "leadscore": {

&#x20;     "command": "python",

&#x20;     "args": \["path/to/mcp\_server.py"]

&#x20;   }

&#x20; }

}

```



\## License

Internal project — Divigo India Private Limited

