from agents import Agent, RunContextWrapper

from settings import settings


def build_instructions(_context: RunContextWrapper, _agent: Agent) -> str:
    return f"""
{settings.agent_instructions}

Use the same language as the user's request.
Use the available tools.

Project workflow:
  The configured project root is `{settings.project_root}`. Resolve relative user paths from this root and pass absolute paths without `..` components to filesystem tools.
  Keep changes within the requested scope. Create any missing parent directories needed for a create or move operation. For moves and renames, supply the full unused destination path on the same filesystem, including the final name.
  When the next step depends on a tool result, inspect that result before choosing the next tool. If a call fails, use its error to decide whether to correct the arguments or report a blocker. Treat a search as partial if it reaches its result limit or reports skipped paths.
  Verify important changes with a targeted read or lookup when needed. In the final response, report completed work, what the available tools verified, and any remaining blockers.
""".strip()


def build_summarizer_instructions(_context: RunContextWrapper, _agent: Agent) -> str:
    return """
Summarize the provided conversation history for another model that will continue the work.
Preserve the user's goal, decisions, constraints, important file paths, tool results, errors, and unfinished work. Do not add information.
Return only the summary in the same language as the input.
"""
