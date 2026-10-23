"""Deterministic tests for the shared ``lookup_order`` function (no LLM, no network)."""

from mini_support_agent.order_data import MOCK_ORDERS, lookup_order

EXPECTED_KEYS = {"order_id", "status", "item", "estimated_delivery"}


def test_known_order_returns_its_record():
    result = lookup_order("ORD-101")
    assert result is not None, "lookup_order returned None - did you forget a return statement?"
    assert result["order_id"] == "ORD-101"
    assert result["status"] == "delayed"


def test_known_order_has_expected_shape():
    result = lookup_order("ORD-102")
    assert isinstance(result, dict), "lookup_order must return a dict"
    assert set(result) == EXPECTED_KEYS, f"known orders need exactly these keys: {EXPECTED_KEYS}"


def test_order_id_is_normalised():
    assert lookup_order("  ord-101 ") == lookup_order("ORD-101"), (
        "strip surrounding whitespace and upper-case the ID before looking it up"
    )


def test_unknown_order_is_handled_cleanly():
    result = lookup_order(" ord-999 ")
    assert result == {"order_id": "ORD-999", "status": "not_found"}, (
        "unknown orders must return {'order_id': <normalised id>, 'status': 'not_found'} "
        "instead of raising KeyError"
    )


def test_result_is_a_copy_not_the_stored_record():
    result = lookup_order("ORD-100")
    result["status"] = "changed by caller"
    assert MOCK_ORDERS["ORD-100"]["status"] == "delivered", (
        "return a copy (dict(...)) so callers cannot modify the mock dataset"
    )
