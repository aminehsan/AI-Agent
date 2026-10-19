from agents import TResponseInputItem
from openai.types.responses import EasyInputMessageParam

from agent.runner import run_compaction

# def _compact_item(item: TResponseInputItem) -> TResponseInputItem | None:
#     if item.get("type") == "reasoning":
#         return None
#
#     if item.get("type") == "function_call_output":
#         compacted = item.copy()
#         compacted["output"] = "summarized output"
#         return compacted
#
#     return item
#
#
# def _compact_inputs(input_items: list[TResponseInputItem]) -> list[TResponseInputItem]:
#     compacted_items: list[TResponseInputItem] = []
#     for item in input_items:
#         compacted_item = _compact_item(item)
#         if compacted_item is not None:
#             compacted_items.append(compacted_item)
#     return compacted_items


async def compact_inputs(input_items: list[TResponseInputItem]) -> list[TResponseInputItem]:
    compacted_items: list[TResponseInputItem] = []
    result = await run_compaction(input_items.copy())
    compacted_items.append(EasyInputMessageParam(role="user", content=result.final_output.strip()))
    return compacted_items
