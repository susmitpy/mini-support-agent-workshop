"""Mock order data and a deterministic order lookup.

The orders below are invented for the workshop. They are not real customers,
orders, or shipments, and nothing here talks to an external system. Both the
Pydantic AI agent and the MCP server call ``lookup_order``, so this module is
the single source of truth for order facts.
"""

MOCK_ORDERS: dict[str, dict[str, str]] = {
    "ORD-100": {
        "order_id": "ORD-100",
        "status": "delivered",
        "item": "Wireless mouse",
        "estimated_delivery": "Delivered on 2026-10-18",
    },
    "ORD-101": {
        "order_id": "ORD-101",
        "status": "delayed",
        "item": "Mechanical keyboard",
        "estimated_delivery": "2026-10-30 (originally 2026-10-24; courier backlog)",
    },
    "ORD-102": {
        "order_id": "ORD-102",
        "status": "shipped",
        "item": "USB-C hub",
        "estimated_delivery": "2026-10-26",
    },
}


def lookup_order(order_id: str) -> dict[str, str]:
    """Look up a mock order by its ID.

    The ID is normalised before lookup: surrounding whitespace is stripped and
    letters are upper-cased, so ``"  ord-101 "`` finds ``"ORD-101"``.

    Args:
        order_id: The order ID the customer gave, e.g. ``"ORD-101"``.

    Returns:
        For a known order, a copy of its record with the keys ``order_id``,
        ``status``, ``item`` and ``estimated_delivery``.

        For an unknown order, ``{"order_id": <normalised id>, "status":
        "not_found"}``. No exception is raised, so callers (and the LLM) always
        get a predictable answer.
    """
    # TODO 1: Implement the lookup in a few lines.
    #   a) Normalise the ID: remove surrounding whitespace and make it upper-case.
    #   b) Look the normalised ID up in MOCK_ORDERS without risking a KeyError.
    #   c) Unknown ID -> return a new dict with the normalised "order_id" and
    #      "status" set to "not_found".
    #   d) Known ID -> return a *copy* of the stored record, so callers can't
    #      accidentally modify MOCK_ORDERS.
    # Check your work with: pytest tests/test_order_data.py
    raise NotImplementedError("TODO 1: implement lookup_order in order_data.py")
