# Civic Lens Backend — Capabilities Reference

## Overview

The Civic Lens backend is a FastAPI application that powers a conversational civic education platform. It manages a 15-level curriculum, AI-driven tutoring, placement assessment, and persistent user progress.

Base URL: `http://localhost:8000`
Interactive API docs: `http://localhost:8000/docs`

---

## Routers

### 1. Conversation (`/api/v1/conversation`)

The core HITL (Human-in-the-Loop) state machine for the learning experience. Each call advances the conversation by one step.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/start` | Start a new session or resume an existing one. Supports `target_level` + `target_mode` to jump directly to any level's lesson or quiz. |
| POST | `/{session_id}/respond` | Send user input (answer choice, free text, nav command) and receive the next agent message, options, and state. |
| GET | `/{session_id}/state` | Retrieve current state and full conversation history for a session. |
| DELETE | `/{session_id}` | End and delete a session. User training progress is preserved. |

**Session States:**
- `start` — Entry point
- `placement_quiz_intro` — Intro message before placement exam
- `placement_quiz_question` — Active placement quiz question (7 questions)
- `placement_quiz_result` — Score + assessed level reveal
- `placement_quiz_review` — Per-question answer review (correct vs selected)
- `lesson_snippet` — Lesson delivery in flash-card snippets with Q&A
- `level_quiz_intro` — Intro before a level quiz
- `level_quiz_question` — Active level quiz question
- `level_quiz_result` — Level quiz score and pass/fail feedback
- `complete` — All levels finished

**Jump-to-Level** (`target_level` + `target_mode`):
```json
POST /api/v1/conversation/start
{ "user_id": "alice", "target_level": 5, "target_mode": "lesson" }
```
Bypasses the placement flow and starts directly at the specified level's lesson or quiz.

---

### 2. Training (`/api/v1/training`)

Manages placement exam, level quizzes, lesson delivery, user status, and the learning roadmap.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/placement/quiz?user_id=` | Get (or resume) the placement quiz for a user. Questions are persisted per-session. |
| POST | `/placement/submit` | Score a completed placement quiz and set the user's starting level. |
| POST | `/lesson` | Deliver the lesson for the user's current level via the GuideAgent. |
| GET | `/quiz?user_id=` | Get (or resume) the level quiz for the user's current level. |
| POST | `/quiz/submit` | Score a level quiz and advance the user to the next level on pass. |
| GET | `/status?user_id=` | Get a user's full training status: current level, completed levels, revision flags, active quiz state. |
| GET | `/roadmap?user_id=` | Get the full 15-level roadmap with titles, descriptions, and per-level status (completed, current, available, locked, needs_revision). |

**Roadmap Level Statuses:**
- `completed` — User has passed the level quiz
- `current` — User's active level
- `available` — Below the current level, not yet completed (unlocked for free exploration)
- `locked` — Above current level
- `needs_revision` — Previously attempted but failed

---

### 3. Curriculum (`/api/v1/curriculum`)

Admin-facing endpoint to generate lesson and quiz content for a specific level using the CurriculumAgent.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate` | Generate lesson content and quiz questions for a given level number. Requires raw text data to be present in `data/`. |

---

### 4. Librarian (`/api/v1/librarian`)

Handles document ingestion into the knowledge base. Uploaded documents are chunked, embedded, and stored in the FAISS vector index.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingest` | Upload a file (PDF, TXT, Python) and ingest it into the knowledge base. Optionally specify a `sub_path` subdirectory. |
| GET | `/status` | Check if the ingestion pipeline is active. |

**Supported file types:** PDF, plain text, Python source files.

---

### 5. Data Manager (`/api/v1/data`)

Manages raw data files and the FAISS vector index.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/files` | List all ingested files and their metadata from the ledger. |
| DELETE | `/files/{filename}` | Delete a file, remove it from the ledger, re-index FAISS, and regenerate curriculum for the affected level. |

---

### 6. Admin (`/api/v1/admin`)

Natural language and direct admin tools for managing lesson content, data files, and embeddings.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ask` | Send a natural language admin request. The AdminAgent interprets and executes the appropriate operation (e.g. "show me the lesson for level 5"). |
| GET | `/lessons` | List all available lessons. |
| GET | `/lessons/{level}` | Get the lesson content for a specific level. |
| PUT | `/lessons/{level}` | Update the lesson content for a level. Optionally regenerate the quiz. |
| GET | `/files` | List raw data files available in the knowledge base. |
| POST | `/files` | Add a new raw data file. |
| POST | `/embeddings/generate` | Trigger embedding generation (re-indexing). Use `force: true` to rebuild from scratch. |

---

### 7. LLM Direct (`/api/v1/llm`)

Low-level endpoint for direct LLM calls via Hugging Face Inference API.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate` | Send a prompt to a Hugging Face model and receive generated text. Default model: `Qwen/Qwen2.5-7B-Instruct`. |

---

## AI Agents

| Agent | Role |
|-------|------|
| `InitialExaminerAgent` | Generates the 7-question placement quiz and evaluates answers to determine starting level (1–15). |
| `GuideAgent` | Delivers lesson content for a given level, split into focused flash-card snippets. Also answers in-lesson Q&A using RAG. |
| `ExaminerAgent` | Generates and evaluates the 7-question level quiz to assess mastery before advancing. |
| `CurriculumAgent` | Generates structured lesson + quiz content from raw text data files for a given level. |
| `AdminAgent` | Interprets natural language admin commands and dispatches to the appropriate tool. |

---

## Data Storage

| Store | Location | Description |
|-------|----------|-------------|
| User profiles | `user_store/profiles/<user_id>.json` | Persistent user progress: level, completed levels, quiz history, revision flags. |
| Sessions | `memory/sessions/<session_id>.json` | Active conversation state, message history, sub-state (quiz answers, snippet index). |
| Lessons | `curriculum/lessons/level_<N>.json` | Generated lesson content for each level. |
| Quizzes | `curriculum/quizzes/level_<N>.json` | Generated quiz questions for each level. |
| Knowledge base | `faiss_index/` | FAISS vector index + embeddings for semantic search. |
| Raw data | `data/` | Source documents used to generate curriculum content. |
| Ledger | `faiss_index/ledger.json` | Tracks ingested files and their associated levels. |

---

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API key for AI agent calls |
| `HUGGINGFACE_API_TOKEN` | Hugging Face token for the direct LLM endpoint |
| `GOOGLE_API_KEY` | (Optional) Google Generative AI key |
