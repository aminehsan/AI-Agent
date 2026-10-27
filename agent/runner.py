from agents import Runner, RunResult, TResponseInputItem

from .config import create_summarizer_run_config
from .factory import create_summarizer_agent


def run_summarizer(summarizer_input: str | list[TResponseInputItem]) -> RunResult:
    run_result = Runner.run_sync(
        starting_agent=create_summarizer_agent(),
        input=summarizer_input,
        max_turns=None,
        run_config=create_summarizer_run_config(),
    )
    return run_result
