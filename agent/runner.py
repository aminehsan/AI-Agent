from agents import Runner, RunResult, TResponseInputItem

from .config import get_run_summarizer_config
from .factory import create_summarizer_agent


async def run_summarizer(input: str | list[TResponseInputItem]) -> RunResult:
    result = await Runner.run(
        starting_agent=create_summarizer_agent(),
        input=input,
        max_turns=None,
        run_config=get_run_summarizer_config(),
    )
    return result
