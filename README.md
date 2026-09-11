# LeadScoreMCP – AI-Powered Sales CRM

LeadScoreMCP is an AI-powered sales lead management and call-analysis system that combines **Model Context Protocol (MCP)**, **Google Gemini AI**, **MySQL**, **Python**, and **RAG (Retrieval-Augmented Generation)** to help sales teams analyze leads, understand customer calls, and make data-driven follow-up decisions.

The system provides structured AI-based lead analysis while using company-specific documents such as FAQs, pricing information, and sales SOPs to generate context-aware responses.

---

## 🚀 Key Features

### 1. Lead Management
- Retrieve all leads from MySQL
- Identify hot and high-priority leads
- View top-performing leads
- Generate lead statistics
- Recommend leads for sales agents

### 2. AI Call Analysis
- Analyze customer call transcripts
- Identify caller intent
- Detect customer sentiment
- Identify sales objections
- Generate call summaries
- Calculate lead scores
- Recommend the next sales action

### 3. RAG-Based Company Knowledge
The system uses **Retrieval-Augmented Generation (RAG)** to provide responses based on company-specific information.

Current knowledge sources include:
- `company_docs/faq.txt`
- `company_docs/pricing.txt`
- `company_docs/sales_sop.txt`

The document ingestion pipeline processes these documents and makes relevant information available to the AI system.

### 4. MCP Integration
The project uses **Model Context Protocol (MCP)** to expose business-specific tools that can be used by AI agents.

Available MCP capabilities include:
- Get all leads
- Get hot leads
- Get top 10 leads
- Get dashboard statistics
- Recommend leads
- Get agent performance
- Analyze call transcripts
- Classify caller intent
- Identify objections
- Calculate lead score
- Recommend next action

### 5. Controlled AI Decision System
Instead of allowing the AI to generate completely unrestricted outputs, the system uses predefined business parameters and validation rules.

The AI analysis is structured around:
- **Intent**
- **Sentiment**
- **Lead Score**
- **Objection Type**
- **Next Action**

This makes the AI output more consistent with sales business requirements.

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │      Web App         │
                    │   Sales Dashboard    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      MCP Server      │
                    │     Python / MCP     │
                    └───────┬───────┬──────┘
                            │       │
                ┌───────────┘       └────────────┐
                ▼                                ▼
       ┌─────────────────┐              ┌─────────────────┐
       │     MySQL       │              │   RAG Pipeline  │
       │  Lead Database  │              │ Company Docs    │
       └─────────────────┘              └────────┬────────┘
                                                  │
                                                  ▼
                                       ┌──────────────────┐
                                       │   Gemini AI      │
                                       │ Context + RAG    │
                                       └────────┬─────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │ Structured AI    │
                                       │ Sales Analysis   │
                                       └──────────────────┘
```

---

## 🧠 RAG Pipeline

```text
Company Documents
       │
       ▼
Document Ingestion
       │
       ▼
Text Processing
       │
       ▼
Chunking
       │
       ▼
Embeddings / Retrieval
       │
       ▼
Relevant Context
       │
       ▼
Gemini AI
       │
       ▼
Context-Aware Response
```

The main ingestion script is `ingest_documents.py`, and company knowledge is stored inside `company_docs/`.

---

## 🛠️ Technology Stack

| Technology              | Purpose                     |
| ----------------------- | ---------------------------- |
| Python                  | Backend and AI processing   |
| MCP                     | AI tool integration          |
| Google Gemini           | AI analysis and generation  |
| MySQL                   | Lead and sales data storage |
| RAG                     | Company knowledge retrieval  |
| HTML / CSS / JavaScript | Web interface                |
| FastAPI                 | AI service/API layer         |
| Git / GitHub            | Version control              |

---

## 📂 Project Structure

```text
LeadScoreMCP-Python/
│
├── agents/
│   └── AI agent components
│
├── company_docs/
│   ├── faq.txt
│   ├── pricing.txt
│   └── sales_sop.txt
│
├── lib/
│   └── chatbot.py
│
├── ingest_documents.py
├── mcp_server.py
├── web_app.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/DeepSunilRathod/LeadScoreMCP.git
cd LeadScoreMCP
```

### 2. Create a virtual environment
```bash
python -m venv .venv
```

### 3. Activate the virtual environment

**Windows**
```bash
.venv\Scripts\activate
```

**Linux / macOS**
```bash
source .venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_gemini_api_key
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=your_database_name
```

**Never commit your `.env` file or API keys to GitHub.**

---

## 📚 Load Company Documents

After adding or modifying documents inside `company_docs/`, run:

```bash
python ingest_documents.py
```

This processes the company knowledge so it can be used by the RAG pipeline.

---

## ▶️ Running the Application

**Start the MCP server**
```bash
python mcp_server.py
```

**Start the web application**
```bash
python web_app.py
```

If the project uses a separate FastAPI AI service, start it according to the service configuration.

---

## 🔍 Example Use Cases

**Sales Lead Prioritization**
```text
High Priority → Hot Lead → Recommended Sales Action
```

**Customer Call Analysis**
```text
Call Recording → Transcription → AI Analysis →
Intent + Sentiment + Objections → Lead Score →
Recommended Next Action
```

**Company Knowledge Assistant**
```text
User Question → Retrieve Relevant Company Information →
Combine Retrieved Context + Question → Gemini AI →
Context-Aware Answer
```

---

## 🎯 Project Objective

The main objective of LeadScoreMCP is to build a **controlled AI-assisted sales system** that combines customer data, call analysis, and company-specific knowledge to support sales teams in:

- Prioritizing leads
- Understanding customer requirements
- Detecting objections
- Evaluating sales opportunities
- Recommending follow-up actions
- Answering questions using company-specific information

---

## 🔒 Security

- API keys stored using environment variables
- `.env` excluded through `.gitignore`
- Database credentials not hard-coded
- Business-specific AI output constraints
- Structured AI responses

---

## 🚧 Future Improvements

- Advanced vector database integration
- Improved semantic search
- Real-time call transcription
- Automated CRM lead updates
- Sales performance analytics
- Authentication and role-based access
- Conversation history
- Improved RAG evaluation
- Production deployment
- Automated lead follow-up recommendations

---

## 👨‍💻 Author

**Deep Sunil Rathod**
Electronics & Telecommunication Engineering Student

GitHub: [https://github.com/DeepSunilRathod](https://github.com/DeepSunilRathod)

---

## ⭐ Support

If you find this project useful, consider giving the repository a ⭐ on GitHub.
