from agents import Agent, RunContextWrapper

from settings import settings


def get_compaction_instructions(_context: RunContextWrapper, _agent: Agent) -> str:
    return """
Compact all provided input items into a concise context for another agent.
Do not add information. Return only the compacted context in the same language as the input.
"""


def get_instructions(_context: RunContextWrapper, _agent: Agent) -> str:
    return f"""
{settings.agent_instructions}
Use the same language as the user's request.
Use the available tools.
""".strip()
