from asyncio import to_thread, run
from agents import RawResponsesStreamEvent, Runner
from openai.types.responses import (
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseTextDeltaEvent,
)
from agent import create_agent


async def main() -> None:
    prompt = (await to_thread(input, "Task: ")).strip()
    print()
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    agent = create_agent()
    result = Runner.run_streamed(starting_agent=agent, input=prompt)
    reasoning_started = False
    answer_started = False
    async for event in result.stream_events():
        if not isinstance(event, RawResponsesStreamEvent):
            continue
        if isinstance(event.data, ResponseReasoningSummaryTextDeltaEvent):
            if not reasoning_started:
                print("Reasoning:")
                reasoning_started = True
            print(event.data.delta, end="", flush=True)
        elif isinstance(event.data, ResponseTextDeltaEvent):
            if not answer_started:
                print("\n\nAnswer:")
                answer_started = True
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
