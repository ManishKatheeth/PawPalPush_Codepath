"""
ReasoningTrace — captures every step of the agent's plan-act-verify loop
so the Streamlit UI can render an observable reasoning timeline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass
class TraceStep:
    """A single observable step in the agent reasoning chain.

    Attributes:
        step_num: 1-indexed position in the trace.
        phase: Which part of the loop this step belongs to.
        timestamp: ISO-8601 UTC timestamp when the step was recorded.
        content: Human-readable one-liner summary shown in the UI.
        raw: Full API/tool payload stored for the "show details" expander.
        duration_ms: Wall-clock time this step took, in milliseconds.
    """

    step_num: int
    phase: Literal["plan", "tool_call", "tool_result", "verify", "replan", "final"]
    timestamp: str
    content: str
    raw: dict[str, Any] | None
    duration_ms: float


@dataclass
class ReasoningTrace:
    """Complete trace for one user turn through the agent loop.

    Attributes:
        request: The raw user message that triggered this trace.
        steps: Ordered list of TraceStep objects.
        final_response: The agent's final answer text returned to the user.
        verifier_result: JSON output from the verifier step.
        total_duration_ms: End-to-end wall-clock time.
        total_tool_calls: Total number of tool invocations across all iterations.
        iterations: How many plan-act-verify cycles ran.
    """

    request: str
    steps: list[TraceStep] = field(default_factory=list)
    final_response: str = ""
    verifier_result: dict[str, Any] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    total_tool_calls: int = 0
    iterations: int = 0

    # Internal: start time for duration tracking
    _start_ms: float = field(default_factory=lambda: time.monotonic() * 1000, repr=False)

    def add_step(
        self,
        phase: Literal["plan", "tool_call", "tool_result", "verify", "replan", "final"],
        content: str,
        raw: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
    ) -> TraceStep:
        """Append a new step and return it.

        Args:
            phase: Which loop phase this step belongs to.
            content: Human-readable summary for UI display.
            raw: Optional full payload for the expander.
            duration_ms: How long this individual step took.

        Returns:
            The newly created TraceStep.
        """
        step = TraceStep(
            step_num=len(self.steps) + 1,
            phase=phase,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=content,
            raw=raw,
            duration_ms=duration_ms,
        )
        self.steps.append(step)
        return step

    def finish(self, final_response: str, verifier_result: dict[str, Any]) -> None:
        """Seal the trace after the loop exits.

        Args:
            final_response: The text returned to the user.
            verifier_result: Parsed verifier JSON.
        """
        self.final_response = final_response
        self.verifier_result = verifier_result
        self.total_duration_ms = time.monotonic() * 1000 - self._start_ms

    def phase_icon(self, phase: str) -> str:
        """Return the emoji icon used for a given phase in the Streamlit UI."""
        icons = {
            "plan": "📋",
            "tool_call": "🔧",
            "tool_result": "📤",
            "verify": "✅",
            "replan": "🔄",
            "final": "💬",
        }
        return icons.get(phase, "•")
