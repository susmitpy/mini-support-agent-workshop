"""Tests for the Pydantic AI agent.

Offline tests use Pydantic AI's ``TestModel`` and ``FunctionModel``, so they need
no API key and cost nothing. Tests marked ``live`` call the real Gemini API and
only run with ``pytest -m live``.
"""

import os

import pytest
from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.messages import ModelMessage, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from mini_support_agent import agent as agent_module
from mini_support_agent.agent import SupportReply, get_order, support_agent
from mini_support_agent.order_data import lookup_order


def tool_returns(messages: list[ModelMessage]) -> list[ToolReturnPart]:
    """Collect every get_order tool result from a run's message history."""
    return [
        part
        for message in messages
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_name == "get_order"
    ]


def test_get_order_tool_is_registered():
    result = support_agent.run_sync("Where is ORD-101?", model=TestModel())
    assert tool_returns(result.all_messages()), (
        "the agent has no get_order tool - see TODO 2a in agent.py"
    )
    assert isinstance(result.output, SupportReply)


def test_agent_tool_uses_shared_lookup():
    assert get_order(" ord-101 ") == lookup_order("ORD-101"), (
        "get_order must return what the shared lookup function returns - see TODO 2b"
    )
    assert get_order("ORD-999")["status"] == "not_found"


def scripted_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Fake LLM: first asks for ORD-101, then answers from the tool's data."""
    returns = tool_returns(messages)
    if not returns:
        return ModelResponse(parts=[ToolCallPart("get_order", {"order_id": "ORD-101"})])
    order = returns[-1].content
    assert isinstance(order, dict), f"get_order did not return order data: {order!r}"
    reply = {
        "order_id": order["order_id"],
        "status": order["status"],
        "explanation": f"Order is {order['status']}.",
        "suggested_reply": "Sorry for the wait.",
    }
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, reply)])


def test_agent_answers_from_tool_data():
    result = support_agent.run_sync("Where is ORD-101?", model=FunctionModel(scripted_model))
    assert result.output.order_id == "ORD-101"
    assert result.output.status == "delayed"


def test_missing_api_key_gives_helpful_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(agent_module, "load_dotenv", lambda: None)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        agent_module.build_model()


@pytest.mark.live
@pytest.mark.parametrize(
    ("question", "order_id", "status"),
    [
        ("Hi, my order ord-101 hasn't arrived yet. What's going on?", "ORD-101", "delayed"),
        ("Can you check order ORD-999 for me?", "ORD-999", "not_found"),
    ],
)
def test_live_gemini_reply(question, order_id, status, capsys):
    result = support_agent.run_sync(question, model=agent_module.build_model())
    reply = result.output

    assert isinstance(reply, SupportReply)
    returns = tool_returns(result.all_messages())
    assert returns, "Gemini answered without calling get_order"
    assert returns[-1].content == lookup_order(order_id), "tool must return the mock record"
    assert reply.order_id == order_id
    assert reply.status == status
    assert reply.explanation.strip() and reply.suggested_reply.strip()

    print(reply.model_dump_json(indent=2))
    api_key = os.environ["GEMINI_API_KEY"]
    assert api_key not in capsys.readouterr().out
    assert api_key not in reply.model_dump_json()
