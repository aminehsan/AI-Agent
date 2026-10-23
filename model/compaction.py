from json import dumps

from agents import TResponseInputItem
from openai.types.responses import EasyInputMessageParam

from agent.runner import run_summarizer


def _str_input(input: list[TResponseInputItem]) -> str:
    return dumps(input, ensure_ascii=False, separators=(",", ":"), default=str)


def _estimate_input_tokens(input: list[TResponseInputItem]) -> int:
    return len(_str_input(input).encode("utf-8")) // 4


def _current_turn_start(input: list[TResponseInputItem]) -> int:
    for index in range(len(input) - 1, -1, -1):
        if input[index].get("phase") == "final_answer":
            return index + 1
    return 1


async def compact_input(input: list[TResponseInputItem]) -> list[TResponseInputItem]:
    if _estimate_input_tokens(input) < 1:
        return input
    current_turn_start = _current_turn_start(input)
    if current_turn_start == 1:
        return input
    old_history = input[:current_turn_start]
    current_turn = input[current_turn_start:]
    summary = await run_summarizer(old_history)
    summary_item = EasyInputMessageParam(
        content=f"Previous conversation summary (context, not a new request):\n{summary.final_output.strip()}",
        role="assistant",
        phase="final_answer",
        type="message",
    )
    return [summary_item, *current_turn]
