from agents import RawResponsesStreamEvent, Runner
from openai.types.responses import (
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseTextDeltaEvent,
)
from app.agent import create_agent
from app.input import get_input
from app.plan import PlanStateError, plan_store
from app.session import create_session


async def _stream_agent(agent, prompt: str, session):
    result = Runner.run_streamed(
        starting_agent=agent,
        input=prompt,
        session=session,
        max_turns=None,
    )
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
    return result


async def run_agent() -> None:
    user_input = await get_input()
    try:
        plan_store.begin_request(user_input)
    except PlanStateError as exc:
        raise SystemExit(f"Cannot start request: {exc}") from exc

    agent = create_agent()
    session = create_session()
    prompt = user_input
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    continuations = 0

    while True:
        result = await _stream_agent(agent, prompt, session)
        usage = result.context_wrapper.usage
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
        total_tokens += usage.total_tokens

        if plan_store.current_request_status() in {"completed", "blocked"}:
            break

        continuations += 1
        print("\n\nPLAN GATE: the request is still active; continuing the agent.")
        print(plan_store.prompt_snapshot())
        prompt = (
            "Continue the active request. The previous response was not final because the "
            "persistent plan is unfinished. Follow the current plan state, review every tool "
            "result, and finish only after the goal is achieved. If the request is impossible, "
            "block the plan with a clear reason before answering."
        )

    print(
        "\n\n"
        f"Token usage:\n"
        f"\tinput={input_tokens}\n"
        f"\toutput={output_tokens}\n"
        f"\ttotal={total_tokens}\n"
        f"\tcontinuations={continuations}"
    )
