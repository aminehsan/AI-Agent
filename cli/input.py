from sys import stdin


def _configure_stdin() -> None:
    if hasattr(stdin, "reconfigure"):
        stdin.reconfigure(encoding="utf-8")


def _format_prompt() -> str:
    prompt = input("\nTask: ").strip()
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    return prompt


def get_input() -> str:
    _configure_stdin()

    _input = _format_prompt()
    return _input
