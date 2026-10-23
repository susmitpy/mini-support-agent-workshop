"""A small customer-support agent built with Pydantic AI and Gemini Flash.

Division of labour:
- Python (``lookup_order``) supplies the authoritative mock order facts.
- The LLM interprets the customer's question, decides to call the tool, and
  drafts an explanation and a reply based only on what the tool returned.

Boundary: the agent only reads mock data. It cannot refund, email, cancel, or
change anything, and its instructions forbid claiming that it did.

Run it with ``python -m mini_support_agent.agent "Where is order ORD-101?"``.
"""

import os
import sys
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from mini_support_agent.order_data import lookup_order  # noqa: F401 (used in your TODO)

# gemini-2.5-flash was the most reliable Flash model in our October 2026
# benchmarks (no 503 overloads). Override with GEMINI_MODEL in .env if needed.
DEFAULT_MODEL_NAME = "gemini-2.5-flash"

# Hide Pydantic AI's observability banner so workshop output stays readable.
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

DEFAULT_QUESTION = "Hi, my order ORD-101 still hasn't arrived. What's going on?"


class SupportReply(BaseModel):
    """Structured answer the agent must return for every customer question.

    Attributes:
        order_id: The normalised order ID the answer is about, e.g. "ORD-101".
        status: The status exactly as reported by the order lookup tool, or
            "not_found" when the tool has no such order.
        explanation: Short internal note for the support team explaining the
            situation, based only on the tool's data.
        suggested_reply: A polite draft message to the customer. It must not
            promise refunds or claim any action was taken.
    """

    order_id: str = Field(description="Normalised order ID, e.g. ORD-101.")
    status: Literal["delivered", "delayed", "shipped", "not_found"] = Field(
        description="Status copied from the order lookup tool."
    )
    explanation: str = Field(description="Brief explanation for the support team.")
    suggested_reply: str = Field(description="Draft reply to send to the customer.")


INSTRUCTIONS = """\
You are a customer-support assistant for a small online shop.
- For any question about an order, call the get_order tool with the order ID.
- Base every statement on the data the tool returns. Never invent dates, items, or reasons.
- If the tool returns status "not_found", say clearly that the order was not found
  and ask the customer to double-check the ID.
- You cannot refund, cancel, email, or change orders. Never claim you did any of these.
"""

support_agent = Agent(output_type=SupportReply, instructions=INSTRUCTIONS)


# TODO 2a: Register get_order as a tool on support_agent by adding a decorator
#   on the line above "def". It needs no RunContext, so use the agent's
#   "plain" tool decorator (see https://ai.pydantic.dev/tools/).
#   Without it, Gemini cannot see the tool and has no order data to work with.
def get_order(order_id: str) -> dict[str, str]:
    """Fetch a mock order record so the agent can answer from real (mock) data.

    Args:
        order_id: The order ID mentioned by the customer, e.g. "ORD-101".

    Returns:
        The order record from ``lookup_order``: order_id, status, item and
        estimated_delivery, or ``{"order_id": ..., "status": "not_found"}``.
    """
    # TODO 2b: Return the order record by calling the shared lookup function
    #   imported at the top of this file. Do not copy the order data here.
    raise NotImplementedError("TODO 2: implement the get_order agent tool in agent.py")


def build_model() -> GoogleModel:
    """Create the Gemini model using the API key from ``.env``.

    Reads ``GEMINI_API_KEY`` (required) and ``GEMINI_MODEL`` (optional).

    Returns:
        A configured ``GoogleModel`` ready to pass to ``support_agent.run_sync``.

    Raises:
        RuntimeError: If ``GEMINI_API_KEY`` is missing. The key itself is never
            printed.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and paste your "
            "Google AI Studio key after GEMINI_API_KEY=."
        )
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME)
    return GoogleModel(model_name, provider=GoogleProvider(api_key=api_key))


def ask(question: str) -> SupportReply:
    """Send one customer question to the agent and return its structured reply.

    Args:
        question: The customer's message in plain language.

    Returns:
        A validated ``SupportReply``.
    """
    result = support_agent.run_sync(question, model=build_model())
    return result.output


def main() -> None:
    """Command-line entry point: answer a question and print the JSON reply."""
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    print(f"Customer: {question}\n")
    try:
        reply = ask(question)
    except ModelHTTPError as error:
        hints = {
            400: "Check that GEMINI_API_KEY in .env is a valid AI Studio key.",
            403: "Check that GEMINI_API_KEY in .env is a valid AI Studio key.",
            429: "Free-tier quota hit; wait a minute and retry.",
            503: "Gemini is overloaded; retry, or set GEMINI_MODEL to another Flash model.",
        }
        hint = hints.get(error.status_code, "See Troubleshooting in README.md.")
        sys.exit(f"Gemini API error {error.status_code} for {error.model_name}. {hint}")
    print(reply.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
