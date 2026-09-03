from asyncio import to_thread, run
from agents import RawResponsesStreamEvent, Runner
from openai.types.responses import ResponseTextDeltaEvent
from agent import create_agent


async def main() -> None:
    prompt = (await to_thread(input, "Task: ")).strip()
    print()
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    agent = create_agent()
    result = Runner.run_streamed(starting_agent=agent, input=prompt)
    async for event in result.stream_events():
        if (
                isinstance(event, RawResponsesStreamEvent)
                and isinstance(event.data, ResponseTextDeltaEvent)
        ):
            print(event.data.delta, end="", flush=True)
    usage = result.context_wrapper.usage
    print(
        "\n\n"
        f"Token usage:\n"
        f"\tinput={usage.input_tokens}\n"
        f"\toutput={usage.output_tokens}\n"
        f"\ttotal={usage.total_tokens}"
    )


if __name__ == "__main__":
    run(main())
