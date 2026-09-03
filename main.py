import asyncio
import openai
import agents
from pathlib import Path
from settings import settings


def create_model():
    if settings.base_url:
        agents.set_tracing_disabled(True)
    client = openai.AsyncOpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key.get_secret_value(),
    )
    return agents.OpenAIResponsesModel(
        model=settings.model,
        openai_client=client,
    )


def get_project_files() -> list[str]:
    project_root = Path(__file__).resolve().parent
    ignored_directories = {".git", ".idea", ".venv", ".vscode", "__pycache__"}
    files = []
    for path in project_root.rglob("*"):
        relative_path = path.relative_to(project_root)
        if not path.is_file():
            continue
        if any(part in ignored_directories for part in relative_path.parts):
            continue
        if relative_path.name == ".env":
            continue
        files.append(relative_path.as_posix())
    return sorted(files)


@agents.function_tool
def list_files() -> str:
    files = get_project_files()
    return "\n".join(files[:200]) or "No files found."


async def main() -> None:
    prompt = (await asyncio.to_thread(input, "Task: ")).strip()
    if not prompt:
        raise SystemExit("Task cannot be empty.")

    agent = agents.Agent(
        name="Coding Assistant",
        model=create_model(),
        tools=[list_files],
        instructions=(
            "Answer programming questions with simple, practical steps. "
            "Use list_files when the user asks about the project files."
        ),
    )

    result = await agents.Runner.run(starting_agent=agent, input=prompt)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
