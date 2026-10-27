from agents import TResponseInputItem


def combines_input_items(
    history_items: list[TResponseInputItem], new_items: list[TResponseInputItem]
) -> list[TResponseInputItem]:
    return [*history_items, *new_items]
