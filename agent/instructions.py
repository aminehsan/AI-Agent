from agents import Agent, RunContextWrapper
from settings import settings


def get_instructions(_context: RunContextWrapper, _agent: Agent) -> str:
    return f"""
{settings.agent_instructions}
Use the same language as the user's request.
Use the available tools.
""".strip()
