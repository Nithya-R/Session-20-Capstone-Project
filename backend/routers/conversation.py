"""
Conversation Router
-------------------
Exposes the conversational Civic Lens training flow as a REST API.

The session is a persistent state machine (ConversationSession + ConversationGraph).
Each POST /respond call advances the state by one step, which may involve an LLM call
(lesson delivery, quiz feedback) or immediate logic (quiz answer collection).

Endpoints:
  POST   /api/v1/conversation/start            - start or resume a session
  POST   /api/v1/conversation/{id}/respond     - send user input, get next agent message
  GET    /api/v1/conversation/{id}/state       - current state + full history
  DELETE /api/v1/conversation/{id}             - end/clear a session

Typical flow:
  1. POST /start -> { session_id, message, options, state }
  2. POST /{id}/respond { "input": "yes" } -> { message, options, state }
  3. ... repeat until state == "complete" or done == true
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.conversation_session import (
    create_session, load_session, delete_session,
    find_session_by_user, append_message,
)
from core.conversation_graph import advance

router = APIRouter(prefix="/conversation", tags=["conversation"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StartRequest(BaseModel):
    user_id: str
    resume: Optional[bool] = True        # resume existing session if one exists
    target_level: Optional[int] = None   # jump directly to a specific level
    target_mode: Optional[str] = None    # "lesson" | "quiz"


class RespondRequest(BaseModel):
    input: str                       # user's reply: "yes" / "a" / "2" / free text


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start")
async def start_conversation(req: StartRequest):
    """
    Start a new conversational session, or resume the most recent active one.

    If resume=true (default) and the user has an existing non-complete session,
    that session is continued from where it left off.

    Returns the first agent message and the session_id to use for future calls.

    Example:
      POST /api/v1/conversation/start
      { "user_id": "alice" }
    """
    # If jumping to a specific level, always create a fresh session
    if req.target_level and req.target_mode:
        session = create_session(req.user_id)
        session["sub_state"] = {
            "target_level": req.target_level,
            "target_mode": req.target_mode,
        }
        from core.conversation_graph import advance_targeted
        result = await advance_targeted(session, req.target_level, req.target_mode)
        return result

    if req.resume:
        session = find_session_by_user(req.user_id)
        if session:
            result = await advance(session)
            return result

    session = create_session(req.user_id)
    result = await advance(session)
    return result


@router.post("/{session_id}/respond")
async def respond(session_id: str, req: RespondRequest):
    """
    Provide user input to advance the conversation by one step.

    Input types:
      - "yes" / "no" / "ready" / "next" / "retry"  — navigational
      - "a" / "b" / "1" / "2"                       — quiz answer choices
      - Free text                                    — acknowledged as-is

    The response always contains:
      - message: the agent's next message
      - state: current state name
      - options: suggested reply options (if any)
      - question: structured question dict (during quiz states)
      - metadata: extra context (level, score, etc.)
      - done: true when state == "complete"

    Example:
      POST /api/v1/conversation/abc12345/respond
      { "input": "a" }
    """
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    # Record the user's message in history
    append_message(session, "user", req.input)

    try:
        result = await advance(session, req.input)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/state")
def get_state(session_id: str):
    """
    Get the current state and full conversation history for a session.
    Useful for rebuilding a UI or debugging.
    """
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {
        "session_id": session_id,
        "user_id": session["user_id"],
        "state": session["state"],
        "sub_state": session["sub_state"],
        "conversation_history": session["conversation_history"],
        "created_at": session["created_at"],
        "last_updated": session["last_updated"],
    }


@router.delete("/{session_id}")
def end_session(session_id: str):
    """
    End and permanently delete a conversation session.
    The user's training progress (in user_store) is NOT affected.
    """
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    delete_session(session_id)
    return {"session_id": session_id, "deleted": True, "message": "Session ended. Training progress preserved."}
