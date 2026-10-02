from sys import stdout

from agents import RunResult, ToolCallItem


def _configure_stdout() -> None:
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")


def _format_usage(result: RunResult) -> str:
    usage = result.context_wrapper.usage
    return (
        "Usage:\n"
        f" requests={usage.requests}\n"
        f" input_tokens={usage.input_tokens}\n"
        f" output_tokens={usage.output_tokens}\n"
        f" total_tokens={usage.total_tokens}"
    )


def _format_tools(result: RunResult) -> str:
    tool_names = [
        item.tool_name
        for item in result.new_items
        if isinstance(item, ToolCallItem) and item.tool_name
    ]
    tools = "\n".join(
        f" {number}. {tool_name}" for number, tool_name in enumerate(tool_names, start=1)
    )
    return f"Tools:\n{tools}"


def _format_answer(result: RunResult) -> str:
    answer = result.final_output.strip()
    return f"Answer:\n{answer}"


def set_output(result: RunResult) -> None:
    _configure_stdout()

    print(f"\n{_format_usage(result)}")
    print(f"\n{_format_tools(result)}")
    print(f"\n{_format_answer(result)}")
