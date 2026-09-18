from sys import stdin


def get_input() -> str:
    if hasattr(stdin, "reconfigure"):
        stdin.reconfigure(encoding="utf-8")
    prompt = input("\nTask: ").strip()
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    return prompt
