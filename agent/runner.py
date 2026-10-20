from agents import Runner, RunResult, TResponseInputItem

from .config import get_run_compaction_config
from .factory import create_compaction_agent


async def run_compaction(input: str | list[TResponseInputItem]) -> RunResult:
    result = await Runner.run(
        starting_agent=create_compaction_agent(),
        input=input,
        max_turns=None,
        run_config=get_run_compaction_config(),
    )
    return result
