from agents import ToolErrorFormatterArgs


def error_formatter(args: ToolErrorFormatterArgs) -> str:
    if args.error is not None:
        return f"Tool '{args.tool_name}' failed with {type(args.error).__name__}: {args.error}"
    return args.default_message
