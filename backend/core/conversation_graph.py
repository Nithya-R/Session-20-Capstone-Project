"""
ConversationGraph
-----------------
State machine for the conversational Civic Lens training flow.

Flow:
  START -> PLACEMENT_QUIZ_INTRO -> PLACEMENT_QUIZ_QUESTION (x7 HITL)
        -> PLACEMENT_QUIZ_RESULT -> (review answers) -> PLACEMENT_QUIZ_REVIEW
        -> LESSON_SNIPPET (snippet 1..N, each with next/prev/ask)
        -> LEVEL_QUIZ_INTRO -> LEVEL_QUIZ_QUESTION (x7 HITL)
        -> LEVEL_QUIZ_RESULT -> next level or retry -> COMPLETE
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.conversation_session import (
    State, save_session, append_message,
)
from user_store.user_hub import (
    load_profile, get_current_level,
    save_active_placement_quiz, load_active_placement_quiz, set_initial_exam_result,
    save_active_level_quiz, load_active_level_quiz, record_level_quiz,
)
from agents.initial_examiner_agent import InitialExaminerAgent
from agents.guide_agent import GuideAgent
from agents.examiner_agent import ExaminerAgent

_initial_examiner = InitialExaminerAgent()
_guide = GuideAgent()
_examiner = ExaminerAgent()

MAX_LEVEL = 15


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------

def _response(session: dict, message: str, options: list = None,
              question: dict = None, metadata: dict = None) -> dict:
    append_message(session, "assistant", message)
    save_session(session)
    return {
        "session_id": session["session_id"],
        "state": session["state"],
        "message": message,
        "options": options or [],
        "question": question,
        "metadata": metadata or {},
        "done": session["state"] == State.COMPLETE,
    }


# ---------------------------------------------------------------------------
# State: START
# ---------------------------------------------------------------------------

async def handle_start(session: dict) -> dict:
    user_id = session["user_id"]
    profile = load_profile(user_id)

    if not profile["initial_exam_completed"]:
        existing = load_active_placement_quiz(user_id)
        if existing:
            session["state"] = State.PLACEMENT_QUIZ_QUESTION
            session["active_questions"] = existing
            session["active_answers"] = {}
            session["sub_state"] = {"question_index": 0}
            q = _format_question(existing[0], 1, len(existing))
            return _response(session,
                "Welcome back! Let's resume your placement assessment.\n\n" + q["text"],
                options=q["options"], question=q)

        session["state"] = State.PLACEMENT_QUIZ_INTRO
        return _response(session,
            "Welcome to Civic Lens! I'm your personal civics guide.\n\n"
            "Before we dive in, I'll ask you 7 quick questions to find the right "
            "starting level for you. This helps us skip what you already know!\n\n"
            "Ready to begin your placement assessment? (yes / no)",
            options=["yes", "no"])

    current_level = profile["current_level"]
    if current_level > MAX_LEVEL:
        session["state"] = State.COMPLETE
        return _response(session, "You've already completed all 15 levels of Civic Lens!")

    session["state"] = State.LESSON_DELIVERY
    return await handle_lesson_delivery(session)


# ---------------------------------------------------------------------------
# State: PLACEMENT_QUIZ_INTRO
# ---------------------------------------------------------------------------

async def handle_placement_quiz_intro(session: dict, user_input: str) -> dict:
    if user_input.strip().lower() in ("yes", "y", "ok", "sure", "ready", "start"):
        questions = _initial_examiner.build_placement_quiz()
        save_active_placement_quiz(session["user_id"], questions)
        session["state"] = State.PLACEMENT_QUIZ_QUESTION
        session["active_questions"] = questions
        session["active_answers"] = {}
        session["sub_state"] = {"question_index": 0}
        q = _format_question(questions[0], 1, len(questions))
        return _response(session, "Great! Here we go.\n\n" + q["text"],
                         options=q["options"], question=q)

    return _response(session, "No problem! Whenever you're ready, just say 'yes' to start.",
                     options=["yes"])


# ---------------------------------------------------------------------------
# State: PLACEMENT_QUIZ_QUESTION
# ---------------------------------------------------------------------------

async def handle_placement_quiz_question(session: dict, user_input: str) -> dict:
    questions = session["active_questions"]
    answers = session["active_answers"]
    idx = session["sub_state"]["question_index"]
    current_q = questions[idx]

    chosen = _parse_answer_choice(user_input, len(current_q["options"]))
    if chosen is None:
        q = _format_question(current_q, idx + 1, len(questions))
        return _response(session,
            f"Please choose A-{chr(64 + len(current_q['options']))} or 1-{len(current_q['options'])}.\n\n" + q["text"],
            options=q["options"], question=q)

    answers[current_q["id"]] = chosen
    session["active_answers"] = answers

    next_idx = idx + 1
    if next_idx < len(questions):
        session["sub_state"] = {"question_index": next_idx}
        next_q = questions[next_idx]
        q = _format_question(next_q, next_idx + 1, len(questions))
        return _response(session,
            f"Question {next_idx + 1} of {len(questions)}:\n\n" + q["text"],
            options=q["options"], question=q)

    return await _score_placement_quiz(session)


async def _score_placement_quiz(session: dict) -> dict:
    questions = session["active_questions"]
    answers = session["active_answers"]
    result = await _initial_examiner.evaluate(questions, answers)
    set_initial_exam_result(session["user_id"], result["overall_score"], result["assessed_level"])

    # Build per-question review data (stored in session for the review state)
    review = []
    for q in questions:
        user_choice = answers.get(q["id"])
        correct_idx = q.get("correct_index")
        review.append({
            "question": q["question"],
            "options": q["options"],
            "user_choice": user_choice,
            "correct_index": correct_idx,
            "correct": user_choice == correct_idx,
            "level": q.get("level"),
        })

    correct_count = sum(1 for r in review if r["correct"])
    total = len(questions)
    assessed = result["assessed_level"]
    feedback = result.get("feedback", "")

    session["state"] = State.PLACEMENT_QUIZ_RESULT
    session["sub_state"] = {"result": result, "review": review}

    msg = (
        f"Placement complete! Score: {correct_count}/{total}\n"
        f"Starting Level: {assessed}\n\n"
        f"{feedback}\n\n"
        f"Would you like to review your answers before starting your first lesson?"
    )
    return _response(session, msg, options=["review answers", "continue"],
                     metadata={"assessed_level": assessed, "score": correct_count, "total": total})


# ---------------------------------------------------------------------------
# State: PLACEMENT_QUIZ_RESULT
# ---------------------------------------------------------------------------

async def handle_placement_quiz_result(session: dict, user_input: str) -> dict:
    if user_input.strip().lower() in ("review", "review answers", "r"):
        session["state"] = State.PLACEMENT_QUIZ_REVIEW
        review = session["sub_state"].get("review", [])
        msg = "Here's how you did on each question. Say 'continue' when you're ready for your first lesson."
        return _response(session, msg, options=["continue"],
                         metadata={"review": review, "type": "quiz_review"})

    session["state"] = State.LESSON_DELIVERY
    return await handle_lesson_delivery(session)


# ---------------------------------------------------------------------------
# State: PLACEMENT_QUIZ_REVIEW
# ---------------------------------------------------------------------------

async def handle_placement_quiz_review(session: dict, user_input: str) -> dict:
    session["state"] = State.LESSON_DELIVERY
    return await handle_lesson_delivery(session)


# ---------------------------------------------------------------------------
# State: LESSON_DELIVERY -> splits lesson into snippets -> LESSON_SNIPPET
# ---------------------------------------------------------------------------

async def handle_lesson_delivery(session: dict) -> dict:
    user_id = session["user_id"]
    current_level = get_current_level(user_id)

    if current_level > MAX_LEVEL:
        session["state"] = State.COMPLETE
        return _response(session, "You've completed all 15 levels! You are a Civic Lens expert!")

    lesson_text = _guide.get_lesson(current_level)

    snippets = _split_lesson(lesson_text)

    session["state"] = State.LESSON_SNIPPET
    session["sub_state"] = {
        "level": current_level,
        "snippets": snippets,
        "snippet_index": 0,
        "full_lesson": lesson_text,
    }

    return _show_snippet(session, 0)


def _split_lesson(text: str) -> list[str]:
    """
    Split lesson into flash-card style snippets: one card per ## section.
    The full content of each section is kept together on a single card.
    The top-level # title is skipped.
    """
    import re

    # Split on ## headings
    raw_sections = re.split(r'\n(?=##\s)', text.strip())
    snippets = []

    for section in raw_sections:
        section = section.strip()
        if not section:
            continue

        heading_line = section.split('\n')[0].strip()

        # Skip the lesson # title card
        if heading_line.startswith('# ') and not heading_line.startswith('## '):
            continue

        snippets.append(section)

    return snippets or [text]


def _show_snippet(session: dict, index: int) -> dict:
    sub = session["sub_state"]
    snippets = sub["snippets"]
    total = len(snippets)
    snippet = snippets[index]
    level = sub["level"]

    sub["snippet_index"] = index

    options = []
    if index > 0:
        options.append("previous")
    if index < total - 1:
        options.append("next")
    options.append("ready for quiz")

    hint = "Type any question to ask about this section, or use the buttons below."
    msg = f"Part {index + 1} of {total}\n\n{snippet}\n\n{hint}"

    return _response(session, msg, options=options,
                     metadata={
                         "type": "lesson_snippet",
                         "snippet_index": index,
                         "total_snippets": total,
                         "level": level,
                     })


# ---------------------------------------------------------------------------
# State: LESSON_SNIPPET
# ---------------------------------------------------------------------------

async def handle_lesson_snippet(session: dict, user_input: str) -> dict:
    sub = session["sub_state"]
    idx = sub["snippet_index"]
    snippets = sub["snippets"]
    inp = user_input.strip().lower()

    if inp in ("next", "n", "continue"):
        if idx + 1 < len(snippets):
            return _show_snippet(session, idx + 1)
        else:
            session["state"] = State.LEVEL_QUIZ_INTRO
            return await handle_level_quiz_intro(session, "ready")

    if inp in ("previous", "prev", "back", "p"):
        return _show_snippet(session, max(0, idx - 1))

    if inp in ("ready", "ready for quiz", "quiz", "done", "skip"):
        session["state"] = State.LEVEL_QUIZ_INTRO
        return await handle_level_quiz_intro(session, "ready")

    # Anything else: treat as a question about this snippet
    return await _answer_lesson_question(session, user_input)


async def _answer_lesson_question(session: dict, question: str) -> dict:
    sub = session["sub_state"]
    idx = sub["snippet_index"]
    snippets = sub["snippets"]
    current_snippet = snippets[idx]
    full_lesson = sub.get("full_lesson", "\n\n".join(snippets))
    total = len(snippets)
    level = sub["level"]

    from core.model_manager import ModelManager
    from config.settings_loader import reload_settings
    cfg = reload_settings().get("agent", {})
    mm = ModelManager(
        cfg.get("default_model", "gemini-2.5-flash-lite"),
        provider=cfg.get("model_provider", "gemini")
    )

    prompt = (
        f"You are a civics tutor. A student reading Level {level} lesson has a question.\n\n"
        f"Current section the student is reading:\n{current_snippet}\n\n"
        f"Full lesson context:\n{full_lesson}\n\n"
        f"Student's question: {question}\n\n"
        f"Answer clearly in 2-4 sentences, using simple language. "
        f"Base your answer on the lesson content above."
    )
    answer = await mm.generate_text(prompt)

    options = []
    if idx > 0:
        options.append("previous")
    if idx < total - 1:
        options.append("next")
    options.append("ready for quiz")

    msg = f"Q: {question}\n\n{answer}"
    return _response(session, msg, options=options,
                     metadata={
                         "type": "lesson_qa",
                         "snippet_index": idx,
                         "total_snippets": total,
                         "level": level,
                     })


# ---------------------------------------------------------------------------
# State: LEVEL_QUIZ_INTRO
# ---------------------------------------------------------------------------

async def handle_level_quiz_intro(session: dict, user_input: str) -> dict:
    if user_input.strip().lower() not in ("ready", "yes", "y", "ok", "start", "quiz", "continue"):
        return _response(session,
            "Take your time reviewing the lesson. Say 'ready' when you want to take the quiz.",
            options=["ready"])

    user_id = session["user_id"]
    current_level = get_current_level(user_id)
    profile = load_profile(user_id)
    attempt_number = len(
        profile.get("level_quiz_history", {}).get(str(current_level), [])
    ) + 1

    existing = load_active_level_quiz(user_id)
    if existing and existing["level"] == current_level:
        questions = existing["questions"]
        resumed = True
    else:
        questions = _examiner.build_level_quiz(current_level)
        save_active_level_quiz(user_id, current_level, questions)
        resumed = False

    session["state"] = State.LEVEL_QUIZ_QUESTION
    session["active_questions"] = questions
    session["active_answers"] = {}
    session["sub_state"] = {
        "question_index": 0,
        "level": current_level,
        "attempt_number": attempt_number,
    }

    prefix = "Resuming" if resumed else "Starting"
    q = _format_question(questions[0], 1, len(questions))
    msg = (
        f"{prefix} Level {current_level} Quiz"
        + (f" (Attempt {attempt_number})" if attempt_number > 1 else "")
        + f"\nPass threshold: 6 out of {len(questions)} correct.\n\n"
        + q["text"]
    )
    return _response(session, msg, options=q["options"], question=q,
                     metadata={"level": current_level, "attempt": attempt_number})


# ---------------------------------------------------------------------------
# State: LEVEL_QUIZ_QUESTION
# ---------------------------------------------------------------------------

async def handle_level_quiz_question(session: dict, user_input: str) -> dict:
    questions = session["active_questions"]
    answers = session["active_answers"]
    idx = session["sub_state"]["question_index"]
    current_q = questions[idx]

    chosen = _parse_answer_choice(user_input, len(current_q["options"]))
    if chosen is None:
        q = _format_question(current_q, idx + 1, len(questions))
        return _response(session,
            f"Please choose A-{chr(64 + len(current_q['options']))} or 1-{len(current_q['options'])}.\n\n" + q["text"],
            options=q["options"], question=q)

    answers[current_q["id"]] = chosen
    session["active_answers"] = answers

    next_idx = idx + 1
    if next_idx < len(questions):
        session["sub_state"]["question_index"] = next_idx
        next_q = questions[next_idx]
        q = _format_question(next_q, next_idx + 1, len(questions))
        return _response(session,
            f"Question {next_idx + 1} of {len(questions)}:\n\n" + q["text"],
            options=q["options"], question=q)

    return await _score_level_quiz(session)


async def _score_level_quiz(session: dict) -> dict:
    sub = session["sub_state"]
    level = sub["level"]
    attempt_number = sub["attempt_number"]
    questions = session["active_questions"]
    answers = session["active_answers"]

    result = await _examiner.evaluate(level, questions, answers, attempt_number)
    record_level_quiz(session["user_id"], level, result["score"], result["total"], result["passed"])

    updated_profile = load_profile(session["user_id"])
    next_level = updated_profile["current_level"]

    # Build per-question review for level quiz too
    review = []
    for q in questions:
        user_choice = answers.get(q["id"])
        correct_idx = q.get("correct_index")
        review.append({
            "question": q["question"],
            "options": q["options"],
            "user_choice": user_choice,
            "correct_index": correct_idx,
            "correct": user_choice == correct_idx,
        })

    session["state"] = State.LEVEL_QUIZ_RESULT
    session["sub_state"] = {"result": result, "level": level, "next_level": next_level, "review": review}

    score = result["score"]
    total = result["total"]
    passed = result["passed"]
    feedback = result.get("feedback", "")

    if passed:
        if next_level > MAX_LEVEL:
            msg = (f"Level {level} - Score: {score}/{total} - PASSED!\n\n{feedback}\n\n"
                   f"You've completed ALL 15 LEVELS! Say 'finish' to see your summary.")
            opts = ["review answers", "finish"]
        else:
            msg = (f"Level {level} - Score: {score}/{total} - PASSED!\n\n{feedback}\n\n"
                   f"Ready for Level {next_level}? Say 'next' to continue.")
            opts = ["review answers", "next"]
    else:
        wrong_count = len(result.get("wrong_questions", []))
        msg = (f"Level {level} - Score: {score}/{total} - Need 6/7 to pass.\n\n{feedback}\n\n"
               f"{wrong_count} wrong. Say 'retry' to try again.")
        opts = ["review answers", "retry"]

    return _response(session, msg, options=opts,
                     metadata={"passed": passed, "score": score, "total": total,
                               "next_level": next_level, "review": review})


# ---------------------------------------------------------------------------
# State: LEVEL_QUIZ_RESULT
# ---------------------------------------------------------------------------

async def handle_level_quiz_result(session: dict, user_input: str) -> dict:
    sub = session["sub_state"]
    result = sub.get("result", {})
    passed = result.get("passed", False)
    next_level = sub.get("next_level", 1)
    inp = user_input.strip().lower()

    if inp in ("review", "review answers"):
        review = sub.get("review", [])
        msg = "Here's how you did. Say 'next', 'retry', or 'finish' when ready."
        opts = ["next"] if passed and next_level <= MAX_LEVEL else ["finish"] if passed else ["retry"]
        return _response(session, msg, options=opts,
                         metadata={"review": review, "type": "quiz_review"})

    if passed:
        if next_level > MAX_LEVEL or inp == "finish":
            session["state"] = State.COMPLETE
            return _response(session, "Congratulations! You've mastered all 15 levels of Civic Lens!")
        session["state"] = State.LESSON_DELIVERY
        return await handle_lesson_delivery(session)
    else:
        session["state"] = State.LEVEL_QUIZ_INTRO
        return await handle_level_quiz_intro(session, "ready")


# ---------------------------------------------------------------------------
# Targeted jump — go directly to lesson or quiz for a specific level
# ---------------------------------------------------------------------------

async def advance_targeted(session: dict, level: int, mode: str) -> dict:
    """
    Jump directly to lesson or quiz for `level`, bypassing the normal flow.
    Used when user clicks a level on the Roadmap.
    """
    from core.conversation_session import State, save_session

    if mode == "lesson":
        session["state"] = State.LESSON_SNIPPET

        lesson_text = _guide.get_lesson(level)
        snippets = _split_lesson(lesson_text)

        session["sub_state"] = {
            "level": level,
            "snippets": snippets,
            "snippet_index": 0,
            "full_lesson": lesson_text,
        }
        return _show_snippet(session, 0)

    elif mode == "quiz":
        from user_store.user_hub import load_profile, save_active_level_quiz
        profile = load_profile(session["user_id"])
        attempt_number = len(
            profile.get("level_quiz_history", {}).get(str(level), [])
        ) + 1

        questions = _examiner.build_level_quiz(level)
        save_active_level_quiz(session["user_id"], level, questions)

        session["state"] = State.LEVEL_QUIZ_QUESTION
        session["active_questions"] = questions
        session["active_answers"] = {}
        session["sub_state"] = {
            "question_index": 0,
            "level": level,
            "attempt_number": attempt_number,
        }

        q = _format_question(questions[0], 1, len(questions))
        msg = (
            f"Level {level} Quiz"
            + (f" (Attempt {attempt_number})" if attempt_number > 1 else "")
            + f"\nPass threshold: 6 out of {len(questions)} correct.\n\n"
            + q["text"]
        )
        return _response(session, msg, options=q["options"], question=q,
                         metadata={"level": level, "attempt": attempt_number})

    else:
        return await advance(session)


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

async def advance(session: dict, user_input: str = None) -> dict:
    state = session["state"]

    if state == State.START:
        return await handle_start(session)
    elif state == State.PLACEMENT_QUIZ_INTRO:
        return await handle_placement_quiz_intro(session, user_input or "")
    elif state == State.PLACEMENT_QUIZ_QUESTION:
        return await handle_placement_quiz_question(session, user_input or "")
    elif state == State.PLACEMENT_QUIZ_RESULT:
        return await handle_placement_quiz_result(session, user_input or "")
    elif state == State.PLACEMENT_QUIZ_REVIEW:
        return await handle_placement_quiz_review(session, user_input or "")
    elif state == State.LESSON_DELIVERY:
        return await handle_lesson_delivery(session)
    elif state == State.LESSON_SNIPPET:
        return await handle_lesson_snippet(session, user_input or "")
    elif state == State.LEVEL_QUIZ_INTRO:
        return await handle_level_quiz_intro(session, user_input or "")
    elif state == State.LEVEL_QUIZ_QUESTION:
        return await handle_level_quiz_question(session, user_input or "")
    elif state == State.LEVEL_QUIZ_RESULT:
        return await handle_level_quiz_result(session, user_input or "")
    elif state == State.COMPLETE:
        return _response(session, "You've completed all levels! Well done, civics expert!")
    else:
        session["state"] = State.ERROR
        save_session(session)
        return _response(session, f"Unexpected state: {state}. Please start a new session.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_question(q: dict, number: int, total: int) -> dict:
    opts = q.get("options", [])
    options_text = "\n".join(f"  {chr(65 + i)}) {opt}" for i, opt in enumerate(opts))
    text = f"Q{number}/{total}: {q['question']}\n\n{options_text}"
    return {
        "id": q["id"],
        "text": text,
        "options": [f"{chr(65 + i)}) {opt}" for i, opt in enumerate(opts)],
        "number": number,
        "total": total,
    }


def _parse_answer_choice(user_input: str, num_options: int) -> int | None:
    inp = user_input.strip().lower()
    if len(inp) >= 2 and inp[1] in (")", "."):
        inp = inp[0]
    if len(inp) == 1 and inp.isalpha():
        idx = ord(inp) - ord("a")
        return idx if 0 <= idx < num_options else None
    try:
        n = int(inp)
        if 1 <= n <= num_options:
            return n - 1
    except ValueError:
        pass
    return None
