from agents import TResponseInputItem


def _compact_item(item: TResponseInputItem) -> TResponseInputItem | None:
    if item.get("type") == "reasoning":
        return None

    if item.get("type") == "function_call_output":
        compacted = item.copy()
        compacted["output"] = "summarized output"
        return compacted

    return item


def compact_input(input_items: list[TResponseInputItem]) -> list[TResponseInputItem]:
    compacted_items: list[TResponseInputItem] = []
    for item in input_items:
        compacted_item = _compact_item(item)
        if compacted_item is not None:
            compacted_items.append(compacted_item)
    return compacted_items
