from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from agents.opposition_agent import OppositionAgent

router = APIRouter(prefix="/simulator", tags=["simulator"])

# A simple mock multi_mcp object since base_agent expects one but opposition doesn't use tools right now
class MockMultiMCP:
    def get_tools_from_servers(self, servers):
        return []

# Initialize the agent
_opposition_agent = OppositionAgent(MockMultiMCP())

class BillProposalRequest(BaseModel):
    title: str
    description: str
    goals: str

@router.post("/evaluate")
async def evaluate_bill(req: BillProposalRequest):
    """
    Submit a bill proposal to the AI Opposition Agent for review.
    Returns constitutional issues, practical flaws, and a rebuttal speech.
    """
    try:
        result = await _opposition_agent.evaluate_bill(
            title=req.title,
            description=req.description,
            goals=req.goals
        )
        return result
    except Exception as e:
        import traceback
        full_tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=str(e) + "\n\n" + full_tb)
