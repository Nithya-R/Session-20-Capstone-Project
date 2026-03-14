# Civic Lens

> **Built for Young Adults** — An adaptive AI-powered platform to learn, explore, and refresh your understanding of India's civic and governance system.

---

## Overview

**Civic Lens** is a multi-agent AI educational platform designed for **young adults** who want to understand or refresh their knowledge of the Indian civic and governance system. Whether you're encountering terms like "Preamble" or "Federalism" for the first time, or brushing up before an exam or election — Civic Lens meets you where you are and guides you through 15 progressive levels at your own pace.

---

## Features

### Adaptive Learning Engine
- **Placement Assessment** — A 7-question diagnostic quiz determines your starting level automatically
- **15-Level Curriculum** — Structured progression from constitutional basics to advanced governance theory
- **Level-Gated Quizzes** — Complete a quiz to unlock the next level
- **XP & Progress Tracking** — Gamified advancement with user profile persistence

### Multi-Agent AI System
| Agent | Role | File |
|-------|------|------|
| **Librarian** | Ingests documents, classifies by level and topic, indexes into FAISS | [`backend/agents/`](backend/agents/) |
| **Initial Examiner** | Generates placement quizzes from scratch | [`backend/agents/initial_examiner_agent.py`](backend/agents/initial_examiner_agent.py) |
| **Examiner** | Delivers level-specific quiz questions and scores answers | [`backend/agents/examiner_agent.py`](backend/agents/examiner_agent.py) |
| **Guide** | Delivers narrative-style lessons tailored to the user's level | [`backend/agents/guide_agent.py`](backend/agents/guide_agent.py) |
| **News Filter** | Fetches and distills local/vernacular governance news | [`backend/agents/news_filter_agent.py`](backend/agents/news_filter_agent.py) |
| **Admin Agent** | Interprets admin commands for curriculum and document management | [`backend/agents/admin_agent.py`](backend/agents/admin_agent.py) |

### Retrieval-Augmented Generation (RAG)
- Documents are chunked, embedded (HuggingFace `all-mpnet-base-v2`), and stored in a local **FAISS** index
- The Q&A agent retrieves relevant chunks and synthesizes cited answers in real time
- Supports PDF ingestion via the Admin Panel

### Local News Lens
- Aggregates news from configured RSS feeds and news sites
- Filters articles relevant to governance, policy, and local civic issues
- Distills complex stories into accessible summaries

### Admin Panel
- Upload PDFs and government documents for auto-ingestion
- Auto-tagging by complexity level (1–15) and topic
- Create, edit, and preview lessons and quizzes per level
- Manage the knowledge repository

### Q&A Service
- Ask open-ended questions about Indian governance
- Answers synthesized from the vector knowledge base and optional web search
- Full Q&A history persisted per user

---

## Curriculum Structure

| Tier | Levels | Topics |
|------|--------|--------|
| **Foundations** | 1–5 | Nation-States, Preamble, Constitution, Three Pillars, Federalism |
| **The Machinery** | 6–10 | Parliament, Executive, Judiciary, Federalism in Action, Elections |
| **Constitutional Deep Dive** | 11–15 | President, PM & Cabinet, State Executives, Fundamental Rights, Crisis Management |
| **Advanced Governance** | *(Coming Soon)* | Party Politics, Parliamentary Procedures, Legislative Nuances, Watchdogs, Governance & You |

Each level contains:
- `lesson.md` — Narrative lesson content
- `quiz.json` — Assessment questions with explanations

See [`backend/curriculum/`](backend/curriculum/) for all level content.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend (Vite)                  │
│   Login → Roadmap → Chat / Admin Panel / News Panel     │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (HTTP/JSON)
┌───────────────────────▼─────────────────────────────────┐
│               FastAPI Backend  /api/v1/                  │
│  ┌──────────┐ ┌──────────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │Conversat-│ │Training  │ │ Q&A  │ │ News │ │Admin │  │
│  │ion Router│ │ Router   │ │Router│ │Router│ │Router│  │
│  └────┬─────┘ └────┬─────┘ └──┬───┘ └──┬───┘ └──┬───┘  │
│       └────────────┴──────────┴────────┴────────┘       │
│  ┌───────────────────────────────────────────────────┐  │
│  │           Services & Agent Orchestration           │  │
│  │  training_service  │  qa_service  │  news_service  │  │
│  └──────────────────┬────────────────────────────────┘  │
│  ┌───────────────────▼────────────────────────────────┐  │
│  │            Conversation State Machine               │  │
│  │  START → PLACEMENT_QUIZ → LESSON → LEVEL_QUIZ → …  │  │
│  └──────────────────┬────────────────────────────────┘  │
│  ┌───────────────────▼────────────────────────────────┐  │
│  │              AI Agents (Google Gemini)              │  │
│  │  InitialExaminer │ Guide │ Examiner │ Librarian     │  │
│  └──────────────────┬────────────────────────────────┘  │
│  ┌───────────────────▼────────────────────────────────┐  │
│  │          Data Layer                                 │  │
│  │  FAISS Index │ User Profiles │ Sessions │ Curriculum │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
My Project - EAG/
├── frontend/                          # React + Vite web app
│   ├── src/
│   │   ├── components/                # UI components
│   │   │   ├── Login.jsx
│   │   │   ├── Roadmap.jsx            # Learning dashboard
│   │   │   ├── Chat.jsx               # Lesson & quiz interface
│   │   │   ├── AdminPanel.jsx         # Admin tools
│   │   │   ├── NewsPanel.jsx          # Local news feed
│   │   │   ├── QuizReview.jsx
│   │   │   └── MessageBubble.jsx
│   │   ├── api.js                     # Backend API client
│   │   └── App.jsx                    # Main router
│   ├── vite.config.js
│   └── package.json
│
├── backend/                           # Python FastAPI backend
│   ├── main.py                        # App entry point + CORS
│   ├── routers/                       # API route handlers
│   │   ├── conversation.py
│   │   ├── training.py
│   │   ├── qa.py
│   │   ├── news.py
│   │   ├── admin.py
│   │   ├── curriculum.py
│   │   └── librarian.py
│   ├── agents/                        # AI agent implementations
│   │   ├── base_agent.py              # AgentRunner orchestrator
│   │   ├── initial_examiner_agent.py
│   │   ├── examiner_agent.py
│   │   ├── guide_agent.py
│   │   ├── curriculum_agent.py
│   │   ├── admin_agent.py
│   │   └── news_filter_agent.py
│   ├── services/                      # Business logic
│   │   ├── training_service.py
│   │   ├── librarian_service.py
│   │   ├── qa_service.py
│   │   ├── news_service.py
│   │   └── indexer_service.py
│   ├── core/                          # Core engine
│   │   ├── conversation_graph.py      # State machine
│   │   ├── conversation_session.py    # Session persistence
│   │   ├── model_manager.py           # LLM provider abstraction
│   │   └── circuit_breaker.py
│   ├── config/                        # Configuration
│   │   ├── settings.json              # System settings
│   │   └── models.json                # Model definitions
│   ├── curriculum/                    # Lesson + quiz content
│   │   └── Level_01/ … Level_15/
│   │       ├── lesson.md
│   │       └── quiz.json
│   ├── user_store/                    # User profiles
│   │   ├── user_hub.py
│   │   └── profiles/
│   ├── memory/                        # Sessions + debug logs
│   │   ├── sessions/
│   │   └── debug_logs/
│   ├── faiss_index/                   # Vector store
│   ├── news_cache/                    # Cached news
│   ├── prompts/                       # Agent prompt templates
│   └── mcp_servers/                   # MCP integrations
│
├── AgentFramework/                    # Reusable agent framework
├── PROJECT_PROPOSAL.md                # Vision & curriculum design
├── IMPLEMENTATION_PLAN.md             # Technical architecture
├── STARTUP.md                         # Dev setup guide
├── ROADMAP.md                         # 4-week execution plan
├── TASKS.md                           # Development checklist
└── TAGGING_CRITERIA.md                # Content classification rules
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, CSS (Glassmorphism) |
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **AI / LLM** | Google Gemini 2.5 Flash (primary), Ollama (fallback) |
| **Embeddings** | HuggingFace `all-mpnet-base-v2` |
| **Vector DB** | FAISS (local) |
| **Data Storage** | JSON files, FAISS indices |
| **Protocol** | MCP (Model Context Protocol) |

---

## Getting Started

See [`STARTUP.md`](STARTUP.md) for full environment setup instructions.

**Quick start:**

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

Set your `GEMINI_API_KEY` environment variable before starting the backend.

---

## User Flow

```
Login
  └── Placement Quiz  (InitialExaminerAgent)
        └── Starting Level Assigned
              └── Roadmap Dashboard
                    ├── Select Level → Chat Interface
                    │     ├── Lesson Delivery  (GuideAgent)
                    │     └── Level Quiz       (ExaminerAgent)
                    │           └── Advance to Next Level
                    ├── Q&A — Ask Anything     (QA Service + RAG)
                    └── Local News Lens        (NewsFilterAgent)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [`PROJECT_PROPOSAL.md`](PROJECT_PROPOSAL.md) | Full vision, 15-level curriculum, data strategy |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Technical architecture and design decisions |
| [`STARTUP.md`](STARTUP.md) | Environment setup and local dev guide |
| [`ROADMAP.md`](ROADMAP.md) | 4-week execution plan |
| [`TASKS.md`](TASKS.md) | Development checklist |
| [`TAGGING_CRITERIA.md`](TAGGING_CRITERIA.md) | Content classification rules for AI tagging |

---

## API Reference

All endpoints are prefixed with `/api/v1/`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/conversation/start` | POST | Start a new learning session |
| `/conversation/{id}/respond` | POST | Submit user input |
| `/training/roadmap` | GET | Fetch user level progress |
| `/training/status` | GET | Current session state |
| `/qa/ask` | POST | Ask a governance question |
| `/qa/history` | GET | Retrieve Q&A history |
| `/admin/data/upload` | POST | Upload document for ingestion |
| `/admin/lessons/{level}` | GET/PUT | Read or update lesson content |
| `/admin/quiz/{level}` | GET/PUT | Read or update quiz questions |
| `/news/sites` | GET | List configured news sources |
| `/news/articles` | GET | Fetch filtered news articles |

