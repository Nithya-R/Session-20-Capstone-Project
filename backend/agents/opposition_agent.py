from agents.base_agent import AgentRunner
from typing import Dict, Any

class OppositionAgent:
    def __init__(self, multi_mcp):
        self.runner = AgentRunner(multi_mcp)
        
    async def evaluate_bill(self, title: str, description: str, goals: str) -> Dict[str, Any]:
        """
        Evaluate a user's proposed bill acting as the parliamentary opposition.
        """
        input_data = {
            "bill_title": title,
            "bill_description": description,
            "goals": goals
        }
        
        result = await self.runner.run_agent(
            agent_type="opposition",
            input_data=input_data
        )
        
        if not result["success"]:
            raise RuntimeError(f"Opposition Agent failed: {result.get('error')}")
            
        return result["output"]
