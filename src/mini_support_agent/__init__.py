"""Mini support agent workshop package.

Contains mock order data, a Pydantic AI agent that uses Gemini, and an MCP
server. The agent and the MCP server both call the same ``lookup_order``
function, so the business logic lives in exactly one place.
"""
