"""Tests for the Pydantic AI agent.

Offline tests use Pydantic AI's ``TestModel`` and the workshop's deterministic
mock LLM, so they need no API key and cost nothing. Tests marked ``live``
call the real Gemini API and only run with ``pytest -m live``.
"""

import os

import pytest
from pydantic_ai.messages import ModelMessage, ToolReturnPart
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.test import TestModel

from mini_support_agent import agent as agent_module
from mini_support_agent.agent import SupportReply, get_order, support_agent
from mini_support_agent.mock_llm import build_mock_model
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


@pytest.mark.parametrize(
    ("question", "order_id", "status"),
    [
        ("Where is my order ord-101?", "ORD-101", "delayed"),
        ("Has ORD-100 arrived?", "ORD-100", "delivered"),
        ("Check ORD-999 please", "ORD-999", "not_found"),
    ],
)
def test_mock_llm_answers_from_tool_data(question, order_id, status):
    result = support_agent.run_sync(question, model=build_mock_model())
    assert tool_returns(result.all_messages()), "the mock LLM should have called get_order"
    assert result.output.order_id == order_id
    assert result.output.status == status


def test_mock_llm_is_deterministic():
    first = support_agent.run_sync("Where is ORD-102?", model=build_mock_model())
    second = support_agent.run_sync("Where is ORD-102?", model=build_mock_model())
    assert first.output == second.output


@pytest.fixture
def no_dotenv(monkeypatch):
    """Ignore the real .env so tests control USE_GEMINI and GEMINI_API_KEY."""
    monkeypatch.setattr(agent_module, "load_dotenv", lambda: None)


def test_mock_llm_is_the_default(monkeypatch, no_dotenv):
    monkeypatch.delenv("USE_GEMINI", raising=False)
    assert agent_module.build_model().model_name == "mock-llm"


def test_use_gemini_switches_to_gemini(monkeypatch, no_dotenv):
    monkeypatch.setenv("USE_GEMINI", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    assert isinstance(agent_module.build_model(), GoogleModel)


def test_missing_api_key_gives_helpful_error(monkeypatch, no_dotenv):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        agent_module.build_gemini_model()


@pytest.mark.live
@pytest.mark.parametrize(
    ("question", "order_id", "status"),
    [
        ("Hi, my order ord-101 hasn't arrived yet. What's going on?", "ORD-101", "delayed"),
        ("Can you check order ORD-999 for me?", "ORD-999", "not_found"),
    ],
)
def test_live_gemini_reply(question, order_id, status, capsys):
    result = support_agent.run_sync(question, model=agent_module.build_gemini_model())
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
