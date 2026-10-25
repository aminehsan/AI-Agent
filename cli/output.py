from sys import stdout

from agents import ReasoningItem, RunResult, ToolCallItem


def _configure_stdout() -> None:
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")


def _format_usage(run_result: RunResult) -> str:
    usage = run_result.context_wrapper.usage
    return (
        "Usage:\n"
        f" requests={usage.requests}\n"
        f" input_tokens={usage.input_tokens}\n"
        f" output_tokens={usage.output_tokens}\n"
        f" total_tokens={usage.total_tokens}"
    )


def _format_tool_calls(run_result: RunResult) -> str:
    tool_names = [
        item.tool_name
        for item in run_result.new_items
        if isinstance(item, ToolCallItem) and item.tool_name
    ]
    formatted_tool_names = "\n".join(
        f" {number}: {tool_name}" for number, tool_name in enumerate(tool_names, start=1)
    )
    return f"Tools:\n{formatted_tool_names}"


def _format_reasoning_summaries(run_result: RunResult) -> str:
    reasoning_summaries = [
        reasoning.text.strip()
        for item in run_result.new_items
        if isinstance(item, ReasoningItem)
        for reasoning in (
            item.raw_item.summary if item.raw_item.summary else item.raw_item.content or []
        )
        if reasoning.text.strip()
    ]
    formatted_summaries = "\n\n".join(
        f"{number})\n{summary}" for number, summary in enumerate(reasoning_summaries, start=1)
    )
    return f"Reasoning:\n{formatted_summaries}"


def _format_final_answer(run_result: RunResult) -> str:
    final_answer = run_result.final_output.strip()
    return f"Answer:\n{final_answer}"


def print_run_result(run_result: RunResult) -> None:
    _configure_stdout()
    print(f"\n{_format_usage(run_result)}")
    print(f"\n{_format_tool_calls(run_result)}")
    print(f"\n{_format_reasoning_summaries(run_result)}")
    print(f"\n{_format_final_answer(run_result)}")
