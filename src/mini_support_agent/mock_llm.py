"""A deterministic stand-in for Gemini, so the workshop runs without an API key.

The mock behaves like a very predictable LLM inside the real Pydantic AI agent
loop:

1. It finds an order ID such as "ORD-101" in the customer's message.
2. It asks the agent to call the ``get_order`` tool with that ID.
3. When the tool result comes back, it fills in ``SupportReply`` from that data.

Because it goes through the same tool call as Gemini would, your ``get_order``
tool and ``lookup_order`` function must work for the mock to answer. The
wording is templated, so the output is identical on every run. Set
``USE_GEMINI=true`` in ``.env`` to switch to the real model.
"""

import re

from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

ORDER_ID_PATTERN = re.compile(r"\bORD-\d+\b", re.IGNORECASE)


def _latest_user_prompt(messages: list[ModelMessage]) -> str:
    """Return the text of the most recent customer message."""
    for message in reversed(messages):
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    return part.content
    return ""


def _latest_order_record(messages: list[ModelMessage]) -> dict[str, str] | None:
    """Return the most recent get_order tool result, or None if there is none yet."""
    for message in reversed(messages):
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name == "get_order":
                    return part.content
    return None


def _reply_from_order(order: dict[str, str]) -> dict[str, str]:
    """Turn a tool result into SupportReply fields using fixed templates."""
    order_id, status = order["order_id"], order["status"]
    if status == "not_found":
        return {
            "order_id": order_id,
            "status": status,
            "explanation": f"No order with ID {order_id} exists in the order system.",
            "suggested_reply": (
                f"I couldn't find an order with ID {order_id}. "
                "Could you double-check the order number?"
            ),
        }
    return {
        "order_id": order_id,
        "status": status,
        "explanation": (
            f"Order {order_id} ({order['item']}) is {status}. "
            f"Estimated delivery: {order['estimated_delivery']}."
        ),
        "suggested_reply": (
            f"Thanks for your patience! Your {order['item']} (order {order_id}) is "
            f"{status}. Estimated delivery: {order['estimated_delivery']}."
        ),
    }


def _mock_llm(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Decide the mock's next step: call get_order, or return the final answer."""
    output_tool = info.output_tools[0].name
    order = _latest_order_record(messages)
    if order is not None:
        return ModelResponse(parts=[ToolCallPart(output_tool, _reply_from_order(order))])

    match = ORDER_ID_PATTERN.search(_latest_user_prompt(messages))
    if match is None:
        no_id_reply = {
            "order_id": "UNKNOWN",
            "status": "not_found",
            "explanation": "The customer did not mention an order ID.",
            "suggested_reply": "Could you share your order ID (for example ORD-101)?",
        }
        return ModelResponse(parts=[ToolCallPart(output_tool, no_id_reply)])

    if "get_order" not in {tool.name for tool in info.function_tools}:
        raise RuntimeError(
            "Mock LLM: the agent has no get_order tool to call, so it has no order data. "
            "Register the tool in agent.py (TODO 2)."
        )
    return ModelResponse(parts=[ToolCallPart("get_order", {"order_id": match.group(0)})])


def build_mock_model() -> FunctionModel:
    """Create the deterministic mock model used when USE_GEMINI is not true.

    Returns:
        A Pydantic AI ``FunctionModel`` that needs no API key or network access.
    """
    return FunctionModel(_mock_llm, model_name="mock-llm")
