def get_input() -> str:
    prompt = input("Task: ").strip()
    print()
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    return prompt
