"""MCP server that exposes the mock order lookup as a discoverable tool.

Any MCP client (Claude Desktop, an IDE, another agent) can
list this server's tools and call ``get_order``. The tool reuses
``lookup_order``, the same function the Pydantic AI agent uses, so there is one
dataset and one copy of the business logic. No Gemini key is needed here.

Run it with ``python -m mini_support_agent.server`` (stdio transport).
"""

from mcp.server import MCPServer

from mini_support_agent.order_data import lookup_order  # noqa: F401 (used in your TODO)

mcp_server = MCPServer(
    name="mini-support-orders",
    instructions="Look up mock shop orders by ID. Data is fake and read-only.",
)


# TODO 3a: Expose get_order as an MCP tool by adding mcp_server's tool decorator
#   on the line above "def" (note: in MCP SDK v2 this decorator is called,
#   i.e. it has parentheses). The function name becomes the tool name and the
#   docstring becomes the description clients see when they list tools.
def get_order(order_id: str) -> dict[str, str]:
    """Look up a mock order by ID (read-only, fake workshop data).

    Args:
        order_id: Order ID such as "ORD-101". Case and surrounding spaces are ignored.

    Returns:
        The order's order_id, status, item and estimated_delivery, or
        {"order_id": ..., "status": "not_found"} if the order does not exist.
    """
    # TODO 3b: Return the result of the shared lookup function imported above,
    #   the same one the agent uses. Do not add a second dataset.
    raise NotImplementedError("TODO 3: implement the get_order MCP tool in server.py")


def main() -> None:
    """Start the MCP server on stdio.

    With stdio, stdout carries the MCP protocol messages, so never print() here;
    write any diagnostics to stderr instead.
    """
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
