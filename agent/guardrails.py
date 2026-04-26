"""
Input, output, and action guardrails for the PawPal+ agent.

Guardrails are lightweight filters that run synchronously (no LLM calls)
to catch obvious problems before they enter or exit the agent loop.
"""

from __future__ import annotations

import re
from typing import Any

from pawpal_system import Owner

# ---------------------------------------------------------------------------
# Off-topic keywords — simple heuristic (not exhaustive)
# ---------------------------------------------------------------------------
_OFF_TOPIC_PATTERNS = re.compile(
    r"\b(stock|weather|recipe|joke|poem|song|sports|politics|news|movie|music)\b",
    re.IGNORECASE,
)

_PET_CARE_PATTERNS = re.compile(
    r"\b(pet|cat|dog|rabbit|bird|fish|hamster|task|feed|walk|vet|groom|schedule|"
    r"reminder|medication|bath|play|exercise|brush|nail|litter|water|cage|cage)\b",
    re.IGNORECASE,
)

# Destructive tool names that need the confirmed flag
_DESTRUCTIVE_TOOLS = {"delete_pet"}
# Tools that are considered mass-reschedule when count exceeds threshold
_RESCHEDULE_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Input guardrail
# ---------------------------------------------------------------------------

class InputGuardrailError(Exception):
    """Raised when input fails validation; message is user-visible."""


def check_input(text: str) -> None:
    """Validate a raw user message before it enters the agent loop.

    Args:
        text: The raw user input string.

    Raises:
        InputGuardrailError: With a friendly, user-visible message when the
            input should be rejected.
    """
    if not text or not text.strip():
        raise InputGuardrailError(
            "Please type a message. I can help you schedule and manage pet care tasks!"
        )

    if len(text) > 2000:
        raise InputGuardrailError(
            "Your message is too long (max 2000 characters). "
            "Please shorten it and try again."
        )

    # Off-topic: contains clearly off-topic keywords AND no pet-care keywords
    if _OFF_TOPIC_PATTERNS.search(text) and not _PET_CARE_PATTERNS.search(text):
        raise InputGuardrailError(
            "I'm PawPal+, your pet care scheduling assistant. "
            "I can help with scheduling tasks, managing pets, and checking your care calendar. "
            "How can I help with your pets today?"
        )


# ---------------------------------------------------------------------------
# Output guardrail
# ---------------------------------------------------------------------------

def check_output(response_text: str, owner: Owner) -> list[str]:
    """Scan the agent's final response for hallucinated pet/entity names.

    Args:
        response_text: The text the agent is about to return to the user.
        owner: The current owner, used to get the real list of pet names.

    Returns:
        A list of warning strings describing problems found.  Empty means clean.
    """
    issues: list[str] = []
    real_names = {p.name.lower() for p in owner.get_pets()}

    # Look for quoted names or capitalised words that resemble pet names
    # and are NOT in the real pet list
    candidates = re.findall(r"'([A-Z][a-z]{1,15})'", response_text)
    for candidate in candidates:
        if candidate.lower() not in real_names and _looks_like_pet_name(candidate):
            issues.append(
                f"Possible hallucinated pet name in response: '{candidate}' "
                "does not match any registered pet."
            )

    return issues


def _looks_like_pet_name(word: str) -> bool:
    """Heuristic: short capitalised word that isn't a common English word."""
    common_words = {
        "The", "And", "For", "Pet", "Task", "Here", "Your", "You", "All",
        "Today", "This", "That", "Now", "New", "Old", "Due", "Done", "Once",
        "Daily", "Weekly", "Please", "Sure", "Great", "Good", "Note", "Also",
    }
    return word not in common_words and len(word) <= 12


# ---------------------------------------------------------------------------
# Action guardrail
# ---------------------------------------------------------------------------

def check_action(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Check whether a tool call needs confirmation before executing.

    Args:
        tool_name: The tool being invoked.
        tool_input: The input dict for that tool.

    Returns:
        A confirmation-request string if the action should be blocked
        until the user confirms, otherwise None (proceed normally).
    """
    if tool_name in _DESTRUCTIVE_TOOLS:
        if not tool_input.get("confirmed"):
            return (
                f"⚠️ The '{tool_name}' action is destructive and cannot be undone. "
                "I won't proceed unless you explicitly confirm. "
                "Please reply 'yes, confirm' or similar to proceed."
            )

    return None


# ---------------------------------------------------------------------------
# Rate-limit guardrail
# ---------------------------------------------------------------------------

class RateLimitError(Exception):
    """Raised when the tool-call count exceeds MAX_TOOL_CALLS in one turn."""


def check_tool_call_count(count: int, max_calls: int) -> None:
    """Raise RateLimitError if count exceeds max_calls.

    Args:
        count: Current number of tool calls in this turn.
        max_calls: The configured per-turn limit.

    Raises:
        RateLimitError: If count >= max_calls.
    """
    if count >= max_calls:
        raise RateLimitError(
            f"Too many tool calls in a single turn ({count}/{max_calls}). "
            "The request is too complex to process safely. "
            "Please break it into smaller steps."
        )
