from agents import Agent, RunContextWrapper

from settings import settings


def get_instructions(_context: RunContextWrapper, _agent: Agent) -> str:
    return f"""
{settings.agent_instructions}
Use the same language as the user's request.
Use the available tools.
""".strip()


def get_summarizer_instructions(_context: RunContextWrapper, _agent: Agent) -> str:
    return """
Summarize the provided conversation history for another model that will continue the work.
Preserve the user's goal, decisions, constraints, important file paths, tool results, errors, and unfinished work. Do not add information.
Return only the summary in the same language as the input.
"""
