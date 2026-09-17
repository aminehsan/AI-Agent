from agents import Agent
from settings import settings
from agent.model import create_model
from tools.filesystem import edit_file, list_files, read_file, write_file, run_command


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        model=create_model(),
        instructions=(
            f"{settings.agent_instructions} "
            "Use the same language as the user's request. Use the available tools when the "
            "request requires inspecting, changing, or running the configured project. Treat "
            "the configured project directory as the project root, use only relative paths, "
            "and read an existing file before changing it. Inspect tool results, correct "
            "failures when possible, and finish with a concise factual answer."
        ),
        tools=[list_files, read_file, write_file, edit_file, run_command],
    )
