from agents import Runner
from asyncio import to_thread, run
from agent import create_agent


async def main() -> None:
    prompt = (await to_thread(input, "Task: ")).strip()
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    agent = create_agent()
    result = await Runner.run(starting_agent=agent, input=prompt)
    usage = result.context_wrapper.usage
    print(
        f"Token usage:\n"
        f"input={usage.input_tokens}\n"
        f"output={usage.output_tokens}\n"
        f"total={usage.total_tokens}\n"
    )
    print(result.final_output)


if __name__ == "__main__":
    run(main())
