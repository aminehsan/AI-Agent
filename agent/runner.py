from agents import Runner, RunResult, TResponseInputItem

from .config import get_run_compaction_config
from .factory import create_compaction_agent


async def run_compaction(input_items: list[TResponseInputItem]) -> RunResult:
    result = await Runner.run(
        starting_agent=create_compaction_agent(),
        input=input_items,
        max_turns=1,
        run_config=get_run_compaction_config(),
    )
    return result
