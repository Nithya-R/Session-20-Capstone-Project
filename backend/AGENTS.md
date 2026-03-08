# Civic Lens — Agent Reference

This document describes every AI agent in the backend, how each is invoked, what model it uses, and whether the frontend interacts with it directly or indirectly.

---

## Agent Overview

| Agent | File | Used by Frontend? | Model |
|-------|------|--------------------|-------|
| InitialExaminerAgent | `agents/initial_examiner_agent.py` | Yes (indirectly via conversation API) | gemini-2.5-flash-lite |
| GuideAgent | `agents/guide_agent.py` | Yes (indirectly via conversation API) | No LLM — reads file directly |
| ExaminerAgent | `agents/examiner_agent.py` | Yes (indirectly via conversation API) | gemini-2.5-flash-lite (feedback only) |
| CurriculumAgent | `agents/curriculum_agent.py` | No (admin/offline only) | gemini-2.5-flash |
| AdminAgent | `agents/admin_agent.py` | No (admin/offline only) | gemini-2.5-flash-lite |
| AgentRunner | `agents/base_agent.py` | No (base class, not used directly) | configurable |

---

## 1. InitialExaminerAgent

**File:** `agents/initial_examiner_agent.py`
**Used by frontend:** Yes — triggered when a user starts a new session before completing placement.

### What it does
Administers the 7-question placement quiz to determine a new user's starting level. Samples 1 question from each of levels 1, 3, 5, 7, 9, 11, 13. Scores answers in pure Python (no LLM), then calls the LLM once to generate personalised feedback.

### Placement logic
- Finds the last *consecutive* alternating level the user answered correctly (starting from level 1).
- `assessed_level = last correct level + 1` (clamped to 1–15).
- If user fails level 1 → starts at level 1. If user passes all → starts at level 15.

### Methods
| Method | Description |
|--------|-------------|
| `build_placement_quiz()` | Returns 7 questions (1 per alternating level) sampled from `curriculum/Level_XX/quiz.json` |
| `_compute_result(questions, answers)` | Pure Python scoring — returns `per_level_results`, `correct_count`, `overall_score`, `assessed_level` |
| `evaluate(questions, answers)` | Full entry point — scores + generates LLM feedback, saves debug log |

### Prompt
`prompts/initial_examiner.md`

### Frontend interaction
The frontend never calls this agent directly. It is invoked by `conversation_graph.py` → `handle_placement_quiz_result()` when the user submits their final placement quiz answer.

The frontend receives the result via `POST /api/v1/conversation/{session_id}/respond` and displays:
- Overall score
- Assessed level
- Option to "review answers" (shows `QuizReview` component)

**If you change placement scoring logic or the assessed_level calculation, update this section.**

---

## 2. GuideAgent

**File:** `agents/guide_agent.py`
**Used by frontend:** Yes — triggered every time a user enters a lesson.

### What it does
Reads the lesson content for a given level and returns it as structured markdown for the flash-card display. **No LLM call is made** — the raw source file is served directly.

### Lesson source priority
1. `data/level{N}.txt` — **primary source** (authoritative, used to generate the quiz)
2. `curriculum/Level_{NN}/lesson.md` — fallback if `.txt` not found

Using `data/levelN.txt` as the primary source ensures the lesson content is always aligned with what the quiz tests, since both originate from the same file.

### Methods
| Method | Description |
|--------|-------------|
| `get_lesson(level)` | Reads and returns raw lesson markdown. Tries `data/levelN.txt` first, falls back to `curriculum/Level_XX/lesson.md` |
| `teach(level, user_name)` | **Deprecated / unused** — previously called LLM to rewrite lesson. Now bypassed in favour of `get_lesson()` |

### Frontend interaction
The frontend never calls this agent directly. It is invoked by `conversation_graph.py`:
- `handle_lesson_delivery()` — normal lesson flow
- `advance_targeted(session, level, "lesson")` — when user clicks **Lesson** on a roadmap card

The lesson text is split into flash-card snippets by `_split_lesson()` in `conversation_graph.py` (one card per `##` section). The frontend (`Chat.jsx`) displays snippets one at a time with **Previous / Next / Ready for Quiz** buttons.

**If you change the lesson source, snippet splitting logic, or lesson navigation buttons in `Chat.jsx`, update this section.**

---

## 3. ExaminerAgent

**File:** `agents/examiner_agent.py`
**Used by frontend:** Yes — triggered when a user takes a level quiz.

### What it does
Administers a 7-question level quiz sampled from the 25-question pool in `curriculum/Level_XX/quiz.json`. Scores answers in pure Python. Calls LLM once to generate personalised feedback. Pass threshold: **6 out of 7 correct**.

### Methods
| Method | Description |
|--------|-------------|
| `build_level_quiz(level)` | Randomly samples 7 questions from `curriculum/Level_XX/quiz.json` |
| `_score(questions, answers)` | Pure Python scoring — returns `score`, `total`, `passed`, `wrong_questions` |
| `_generate_feedback(level, scored, attempt_number)` | LLM call to generate personalised pass/fail feedback |
| `evaluate(level, questions, answers, attempt_number)` | Full entry point — scores + feedback + debug log |

### Prompt
`prompts/examiner_agent.md`

### Frontend interaction
The frontend never calls this agent directly. It is invoked by `conversation_graph.py`:
- `handle_level_quiz_result()` — scores the quiz after the 7th answer
- `advance_targeted(session, level, "quiz")` — when user clicks **Quiz** on a roadmap card

The frontend displays the result via `Chat.jsx`:
- Score and pass/fail message
- Option to "review answers" → shows `QuizReview.jsx` (per-question correct/wrong breakdown)
- On pass: advances to next level
- On fail: flags level for revision, offers retry

**If you change the pass threshold, quiz size, or the `QuizReview` display in `Chat.jsx`, update this section.**

---

## 4. CurriculumAgent

**File:** `agents/curriculum_agent.py`
**Used by frontend:** No — admin/offline tool only.

### What it does
Generates structured lesson content (`lesson.md`) and a 25-question quiz (`quiz.json`) for a given level from raw source text. Called via the admin API endpoint.

### Workflow
1. `CurriculumService.generate_level(N)` reads raw text from `data/` (via ledger or `data/levelN.txt`)
2. Calls `CurriculumAgent.run({ action: "create_lesson", raw_text })` → saves `curriculum/Level_NN/lesson.md`
3. Calls `CurriculumAgent.run({ action: "create_quiz", lesson_text })` → saves `curriculum/Level_NN/quiz.json`

### API endpoint
`POST /api/v1/curriculum/generate` — body: `{ "level": N }`

### Prompt
`prompts/curriculum_designer_agent.md` (referenced via `config/agent_config.yaml`)

### Important notes
- The quiz is generated from `lesson.md`, which is itself generated from `data/levelN.txt`.
- **Always regenerate lesson and quiz together** — running only one can cause misalignment.
- After regeneration, the new `lesson.md` is only used as a fallback. The frontend will still serve `data/levelN.txt` as the primary lesson source (via GuideAgent).

---

## 5. AdminAgent

**File:** `agents/admin_agent.py`
**Used by frontend:** No — admin/offline tool only.

### What it does
Interprets natural language admin requests and dispatches them to the correct admin service function. Acts as an NL interface over the admin tools.

### Supported tools (dispatched to `AdminService`)
| Tool | Description |
|------|-------------|
| `list_lessons` | List all available lessons |
| `get_lesson` | Fetch lesson content for a level |
| `update_lesson` | Update lesson content, optionally regenerate quiz |
| `list_data_files` | List raw source files |
| `add_data_file` | Add a new raw data file |
| `delete_data_file` | Remove a file |
| `generate_embeddings` | Trigger FAISS re-indexing |

### API endpoint
`POST /api/v1/admin/ask` — body: `{ "request": "show me the lesson for level 5" }`

### Prompt
`prompts/admin_agent.md`

---

## 6. AgentRunner (Base Class)

**File:** `agents/base_agent.py`
**Used by frontend:** No — base infrastructure only.

### What it does
Generic agent runner that loads `config/agent_config.yaml`, manages ModelManager setup, handles MCP tool calls, and calculates LLM token costs. Provides the common execution loop for agents that use MCP tools.

### Not directly instantiated by the learning flow
The learning agents (InitialExaminerAgent, GuideAgent, ExaminerAgent) are standalone classes that do not extend AgentRunner. CurriculumAgent and AdminAgent also operate independently.

---

## 7. Q&A RAG (Roadmap Q&A Tab)

**Files:** `services/qa_service.py`, `routers/qa.py`
**Used by frontend:** Yes — the **Ask Q&A** tab on the Roadmap page.

### What it does
Answers free-form civic knowledge questions using hybrid FAISS search (semantic embeddings) to retrieve relevant document chunks, then passes them as context to Gemini for a grounded answer. Persists each question to the user's profile for suggestion bubbles on future visits.

### API endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/qa/ask` | `{ user_id, question }` → `{ answer, sources, history }` |
| GET | `/api/v1/qa/history?user_id=` | Returns the user's past questions list |

### Question history
- Stored in `user_store/profiles/<user_id>.json` under `qa_history` (max 30 entries, newest first, duplicates moved to top)
- Loaded on roadmap open and displayed as suggestion chips
- Clicking a suggestion chip re-asks that question immediately

### Frontend interaction
- `Roadmap.jsx` — "💬 Ask Q&A" tab in the center panel
- `api.js` — `askQuestion(userId, question)` and `getQAHistory(userId)`
- Answer is shown as a blue-bordered card with a collapsible **Sources** section showing the retrieved FAISS chunks
- After answering, a "Ask another question" link clears the answer and shows the input again

**If you change the RAG search logic, answer prompt, or the Q&A UI in `Roadmap.jsx`, update this section.**

---

## Frontend ↔ Agent Call Map

```
User action in browser
        │
        ▼
POST /api/v1/conversation/start
POST /api/v1/conversation/{id}/respond
        │
        ▼
conversation_graph.py  (HITL state machine)
        │
        ├── handle_start()
        │       └── (no agent call — checks user profile)
        │
        ├── handle_placement_quiz_result()
        │       └── InitialExaminerAgent.evaluate()
        │               └── LLM: feedback only
        │
        ├── handle_lesson_delivery()
        ├── advance_targeted(..., "lesson")
        │       └── GuideAgent.get_lesson()
        │               └── reads data/levelN.txt (NO LLM)
        │
        ├── handle_level_quiz_result()
        ├── advance_targeted(..., "quiz")
        │       └── ExaminerAgent.evaluate()
        │               └── LLM: feedback only
        │
        └── _answer_lesson_question()
                └── Direct LLM call (Gemini) — in-lesson Q&A

POST /api/v1/qa/ask  (Roadmap Q&A tab)
GET  /api/v1/qa/history
        │
        ▼
qa_service.py
        ├── search_stored_documents_rag_civic(question)
        │       └── FAISS hybrid search → top-k chunks
        └── ModelManager.generate_text(context + question)
                └── LLM: grounded answer from retrieved chunks
```

---

## Change Log

| Date | Change | Affected Agent | Frontend Impact |
|------|--------|----------------|-----------------|
| 2026-03-08 | Removed LLM rewrite from lesson delivery — GuideAgent.get_lesson() now serves raw file directly | GuideAgent | Lesson flash-cards now show original source content instead of LLM-paraphrased text |
| 2026-03-08 | Changed lesson source priority: `data/levelN.txt` > `curriculum/Level_XX/lesson.md` | GuideAgent | Ensures lesson and quiz are always from the same source, eliminating content mismatches |
| 2026-03-08 | `_split_lesson()` changed from "max 4 lines per card" to "one card per ## section" | GuideAgent (consumer) | Each lesson topic now appears as a single complete flash-card instead of being split mid-topic |
