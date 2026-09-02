import sys
from pathlib import Path
from settings import settings
from openai import AsyncOpenAI
from agents import (
    Agent,
    OpenAIResponsesModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)

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
    files = get_project_files()
    return "\n".join(files[:200]) or "No files found."


def create_model():
    if settings.base_url:
        set_tracing_disabled(True)
    client = AsyncOpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key.get_secret_value(),
    )
    return OpenAIResponsesModel(
        model=settings.model,
        openai_client=client,
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
