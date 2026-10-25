from agents import ToolErrorFormatterArgs


def format_tool_error(error_context: ToolErrorFormatterArgs) -> str:
    if error_context.error is not None:
        return (
            f"Tool '{error_context.tool_name}' failed with "
            f"{type(error_context.error).__name__}: {error_context.error}"
        )
    return error_context.default_message
