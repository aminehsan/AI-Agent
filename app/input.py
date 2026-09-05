from asyncio import to_thread


async def get_input() -> str:
    prompt = (await to_thread(input, "Task: ")).strip()
    print()
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    return prompt
