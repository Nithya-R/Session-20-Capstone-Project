import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.resolve()))
import asyncio
from agents.opposition_agent import OppositionAgent

class MockMultiMCP:
    def get_tools_from_servers(self, servers):
        return []

async def test():
    agent = OppositionAgent(MockMultiMCP())
    result = await agent.evaluate_bill("The Mandatory Voting Act", "Everyone votes or pays 5k", "To ensure 100% turnout")
    print(result)

if __name__ == '__main__':
    asyncio.run(test())
