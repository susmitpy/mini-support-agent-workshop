"""Protocol-level tests for the MCP server.

These use the official MCP Python client, first in memory and then over real
stdio (the same transport the MCP Inspector uses). No API key is needed.
"""

import sys

import pytest
from mcp import Client, StdioServerParameters

from mini_support_agent.order_data import lookup_order
from mini_support_agent.server import mcp_server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_get_order_tool_is_discoverable():
    async with Client(mcp_server) as client:
        tools = await client.list_tools()
    names = [tool.name for tool in tools.tools]
    assert "get_order" in names, "get_order is not an MCP tool yet - see TODO 3a in server.py"
    tool = next(tool for tool in tools.tools if tool.name == "get_order")
    assert tool.description, "give the MCP tool a docstring so clients know what it does"
    assert tool.input_schema["required"] == ["order_id"]


async def test_mcp_tool_uses_shared_lookup():
    async with Client(mcp_server) as client:
        known = await client.call_tool("get_order", {"order_id": " ord-101 "})
        unknown = await client.call_tool("get_order", {"order_id": "ORD-999"})
    assert not known.is_error, f"MCP tool call failed: {known.content}"
    assert known.structured_content == lookup_order("ORD-101"), (
        "the MCP tool must return what the shared lookup function returns - see TODO 3b"
    )
    assert unknown.structured_content == {"order_id": "ORD-999", "status": "not_found"}


async def test_server_works_over_stdio():
    params = StdioServerParameters(command=sys.executable, args=["-m", "mini_support_agent.server"])
    async with Client(params) as client:
        result = await client.call_tool("get_order", {"order_id": "ORD-102"})
    assert result.structured_content == lookup_order("ORD-102")
