import os
import sys
from pathlib import Path

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    OpenAIResponsesModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from openai import AsyncOpenAI


DEFAULT_MODEL = "gpt-5.6-terra"
PROJECT_ROOT = Path(__file__).resolve().parent
IGNORED_DIRECTORIES = {".git", ".idea", ".venv", ".vscode", "__pycache__"}


def get_project_files() -> list[str]:
    files = []

    for path in PROJECT_ROOT.rglob("*"):
        relative_path = path.relative_to(PROJECT_ROOT)

        if not path.is_file():
            continue
        if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
            continue
        if relative_path.name == ".env":
            continue

        files.append(relative_path.as_posix())

    return sorted(files)


@function_tool
def list_files() -> str:
    """List files in the project without reading their contents."""
    files = get_project_files()
    return "\n".join(files[:200]) or "No files found."


def create_model():
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    api_mode = os.getenv("OPENAI_API_MODE", "responses").lower()
    model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    if not api_key and not base_url:
        raise SystemExit("OPENAI_API_KEY is not set.")

    client_options = {"api_key": api_key or "not-needed"}
    if base_url:
        client_options["base_url"] = base_url
        set_tracing_disabled(True)

    client = AsyncOpenAI(**client_options)

    if api_mode == "responses":
        return OpenAIResponsesModel(model=model_name, openai_client=client)
    if api_mode == "chat_completions":
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    raise SystemExit(
        "OPENAI_API_MODE must be 'responses' or 'chat_completions'."
    )


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip()
    if not prompt:
        prompt = input("Task: ").strip()

    if not prompt:
        raise SystemExit("Task cannot be empty.")

    agent = Agent(
        name="Coding Assistant",
        instructions=(
            "Answer programming questions with simple, practical steps. "
            "Use list_files when the user asks about the project files."
        ),
        model=create_model(),
        tools=[list_files],
    )
    result = Runner.run_sync(agent, prompt)
    print(result.final_output)


if __name__ == "__main__":
    main()
