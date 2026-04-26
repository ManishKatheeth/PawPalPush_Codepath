"""
Unit tests for agent/guardrails.py — input, output, and action guardrails.
"""

from __future__ import annotations

import uuid

import pytest

from pawpal_system import Owner, Pet
from agent.guardrails import (
    InputGuardrailError,
    RateLimitError,
    check_action,
    check_input,
    check_output,
    check_tool_call_count,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_owner_with_pets() -> Owner:
    owner = Owner(owner_id=str(uuid.uuid4()), name="Tester")
    owner.add_pet(Pet(pet_id=str(uuid.uuid4()), name="Rex", species="Dog"))
    owner.add_pet(Pet(pet_id=str(uuid.uuid4()), name="Mochi", species="Cat"))
    return owner


# ---------------------------------------------------------------------------
# Input guardrail
# ---------------------------------------------------------------------------

class TestCheckInput:
    def test_valid_input_passes(self) -> None:
        check_input("Add a walk for my dog Rex at 9am daily")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(InputGuardrailError):
            check_input("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InputGuardrailError):
            check_input("   ")

    def test_too_long_raises(self) -> None:
        with pytest.raises(InputGuardrailError):
            check_input("x" * 2001)

    def test_exactly_max_length_passes(self) -> None:
        check_input("pet " + "x" * 1996)  # 4 + 1996 = 2000 chars, contains pet keyword

    def test_off_topic_no_pet_keywords_raises(self) -> None:
        with pytest.raises(InputGuardrailError):
            check_input("Tell me the weather forecast for tomorrow")

    def test_joke_request_raises(self) -> None:
        with pytest.raises(InputGuardrailError):
            check_input("Tell me a joke about cars")

    def test_off_topic_but_contains_pet_passes(self) -> None:
        # "stock" is off-topic but "pet" is present → passes (user might be asking
        # about pet-related stock items)
        check_input("I want to stock up on pet food for my dog")

    def test_pet_care_request_passes(self) -> None:
        check_input("Schedule a vet appointment for Mochi on Tuesday")

    def test_ambiguous_short_request_passes(self) -> None:
        # "fix it" — ambiguous but not off-topic; guardrail should pass it through
        check_input("fix it")


# ---------------------------------------------------------------------------
# Output guardrail
# ---------------------------------------------------------------------------

class TestCheckOutput:
    def test_clean_response_no_issues(self) -> None:
        owner = _make_owner_with_pets()
        issues = check_output("I have scheduled a walk for Rex at 9am.", owner)
        assert issues == []

    def test_known_pet_names_not_flagged(self) -> None:
        owner = _make_owner_with_pets()
        issues = check_output("Rex and Mochi both have tasks scheduled.", owner)
        assert issues == []

    def test_hallucinated_pet_name_flagged(self) -> None:
        owner = _make_owner_with_pets()
        # 'Buddy' is not in the owner's pet list
        issues = check_output("I've scheduled a walk for 'Buddy' at 9am.", owner)
        assert len(issues) > 0
        assert any("Buddy" in issue for issue in issues)

    def test_common_words_not_flagged(self) -> None:
        owner = _make_owner_with_pets()
        issues = check_output("'Today' I scheduled 'All' tasks for your pets.", owner)
        assert issues == []

    def test_empty_response_clean(self) -> None:
        owner = _make_owner_with_pets()
        issues = check_output("", owner)
        assert issues == []


# ---------------------------------------------------------------------------
# Action guardrail
# ---------------------------------------------------------------------------

class TestCheckAction:
    def test_delete_pet_without_confirmed_blocked(self) -> None:
        msg = check_action("delete_pet", {"pet_name": "Rex"})
        assert msg is not None
        assert "destructive" in msg.lower() or "confirm" in msg.lower()

    def test_delete_pet_confirmed_allowed(self) -> None:
        msg = check_action("delete_pet", {"pet_name": "Rex", "confirmed": True})
        assert msg is None

    def test_delete_pet_confirmed_false_blocked(self) -> None:
        msg = check_action("delete_pet", {"pet_name": "Rex", "confirmed": False})
        assert msg is not None

    def test_non_destructive_tool_allowed(self) -> None:
        msg = check_action("add_task", {"pet_name": "Rex", "description": "Walk"})
        assert msg is None

    def test_list_pets_always_allowed(self) -> None:
        msg = check_action("list_pets", {})
        assert msg is None


# ---------------------------------------------------------------------------
# Rate-limit guardrail
# ---------------------------------------------------------------------------

class TestCheckToolCallCount:
    def test_under_limit_passes(self) -> None:
        check_tool_call_count(5, 20)  # should not raise

    def test_at_limit_raises(self) -> None:
        with pytest.raises(RateLimitError):
            check_tool_call_count(20, 20)

    def test_over_limit_raises(self) -> None:
        with pytest.raises(RateLimitError):
            check_tool_call_count(25, 20)

    def test_zero_count_passes(self) -> None:
        check_tool_call_count(0, 20)
