"""
PawPal+ agent core — the plan → act → verify → replan loop.

Architecture:
  1. Plan   — Send user request to Claude with planner system prompt.
              Claude emits a <plan> block before calling any tools.
  2. Act    — Run the tool-use loop until stop_reason == "end_turn".
  3. Verify — Separate Claude call: did the agent fully address the request?
              Returns {success, confidence, issues}.
  4. Replan — If verification fails and we haven't hit MAX_REPLAN_ATTEMPTS,
              feed the issues back in and try again.

Every step is appended to a ReasoningTrace for observable UI rendering.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import anthropic

import storage
from pawpal_system import Owner

from . import config
from .guardrails import (
    InputGuardrailError,
    RateLimitError,
    check_input,
    check_output,
    check_tool_call_count,
)
from .prompts import PLANNER_SYSTEM_PROMPT, REPLAN_SYSTEM_PROMPT, VERIFIER_SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, ToolExecutor
from .trace import ReasoningTrace

logger = logging.getLogger(__name__)

# Logging setup — writes to logs/agent.log
_file_handler = logging.FileHandler(config.LOG_FILE)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
)
logging.getLogger().addHandler(_file_handler)
logging.getLogger().setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_agent(
    user_message: str,
    owner: Owner,
    conversation_history: list[dict[str, Any]] | None = None,
    persist: bool = True,
) -> ReasoningTrace:
    """Run the full plan-act-verify-replan loop for one user turn.

    Args:
        user_message: The raw text from the chat input.
        owner: The current Owner instance (reads and mutates state).
        conversation_history: Optional list of prior {role, content} dicts
            (alternating user/assistant) to give Claude context across turns.
        persist: If False, tool mutations are kept in-memory only (used by
            the eval harness to avoid polluting the production data file).

    Returns:
        A fully populated ReasoningTrace that the UI renders as a timeline.
    """
    trace = ReasoningTrace(request=user_message)

    # --- Input guardrail ---
    try:
        check_input(user_message)
    except InputGuardrailError as exc:
        trace.add_step("final", str(exc))
        trace.finish(str(exc), {"success": False, "confidence": 1.0, "issues": [str(exc)]})
        return trace

    if not config.ANTHROPIC_API_KEY:
        msg = (
            "ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env, add your key, and restart."
        )
        trace.add_step("final", msg)
        trace.finish(msg, {"success": False, "confidence": 1.0, "issues": [msg]})
        return trace

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    executor = ToolExecutor(owner=owner, persist=persist)

    best_response = ""
    verifier_result: dict[str, Any] = {}

    for iteration in range(config.MAX_ITERATIONS):
        trace.iterations += 1

        # Build message list: prior history (up to last 10 turns) + current message
        history = (conversation_history or [])[-10:]
        if iteration == 0:
            system_prompt = PLANNER_SYSTEM_PROMPT
            messages: list[dict[str, Any]] = history + [{"role": "user", "content": user_message}]
        else:
            # Replan: inject verifier issues into the system prompt
            system_prompt = REPLAN_SYSTEM_PROMPT.format(
                issues="\n".join(f"- {i}" for i in verifier_result.get("issues", [])),
                original_request=user_message,
                previous_response=best_response,
            )
            messages = history + [{"role": "user", "content": user_message}]

        response_text, tool_call_count, trace = _act_loop(
            client=client,
            executor=executor,
            system_prompt=system_prompt,
            messages=messages,
            trace=trace,
        )

        best_response = response_text

        # --- Verify ---
        verifier_result = _verify(
            client=client,
            user_message=user_message,
            agent_response=response_text,
            trace=trace,
        )

        succeeded = verifier_result.get("success", False)
        confidence = verifier_result.get("confidence", 0.0)

        if succeeded or confidence >= config.REPLAN_CONFIDENCE_THRESHOLD:
            break

        replan_num = iteration + 1
        if replan_num > config.MAX_REPLAN_ATTEMPTS:
            logger.warning("Max replan attempts reached; returning best response.")
            break

        trace.add_step(
            "replan",
            f"Replan #{replan_num}: {', '.join(verifier_result.get('issues', []))}",
            raw=verifier_result,
        )

    # --- Output guardrail ---
    output_issues = check_output(best_response, owner)
    if output_issues:
        logger.warning("Output guardrail flagged issues: %s", output_issues)
        for issue in output_issues:
            verifier_result.setdefault("issues", []).append(issue)

    trace.add_step("final", best_response[:120] + ("…" if len(best_response) > 120 else ""))
    trace.finish(best_response, verifier_result)
    return trace


# ---------------------------------------------------------------------------
# Act loop
# ---------------------------------------------------------------------------

def _act_loop(
    client: anthropic.Anthropic,
    executor: ToolExecutor,
    system_prompt: str,
    messages: list[dict[str, Any]],
    trace: ReasoningTrace,
) -> tuple[str, int, ReasoningTrace]:
    """Run the tool-use loop until the model reaches end_turn.

    Returns:
        (final_text_response, total_tool_calls_this_loop, updated_trace)
    """
    tool_calls_this_loop = 0
    final_text = ""

    while True:
        t0 = time.monotonic()
        response = client.messages.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            system=system_prompt,
            tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
            messages=messages,
        )
        duration_ms = (time.monotonic() - t0) * 1000

        # Collect text blocks and tool-use blocks
        text_blocks = [b for b in response.content if b.type == "text"]
        tool_blocks = [b for b in response.content if b.type == "tool_use"]

        combined_text = "\n".join(b.text for b in text_blocks)

        if combined_text:
            # First text block from the model — capture the <plan> section
            if "<plan>" in combined_text:
                plan_text = _extract_plan(combined_text)
                trace.add_step(
                    "plan",
                    plan_text,
                    raw={"raw_text": combined_text},
                    duration_ms=duration_ms,
                )
            else:
                final_text = combined_text

        if response.stop_reason == "end_turn":
            final_text = final_text or combined_text
            break

        if response.stop_reason != "tool_use" or not tool_blocks:
            final_text = final_text or combined_text
            break

        # Append assistant turn to messages
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call
        tool_results = []
        for block in tool_blocks:
            try:
                check_tool_call_count(trace.total_tool_calls, config.MAX_TOOL_CALLS)
            except RateLimitError as exc:
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True}
                )
                trace.add_step("tool_call", f"ABORTED — {exc}")
                final_text = str(exc)
                break

            t1 = time.monotonic()
            result = executor.execute(block.name, block.input)  # type: ignore[arg-type]
            tool_duration_ms = (time.monotonic() - t1) * 1000

            trace.total_tool_calls += 1
            tool_calls_this_loop += 1

            trace.add_step(
                "tool_call",
                f"{block.name}({_summarise_input(block.input)}) → {_summarise_result(result)}",  # type: ignore[arg-type]
                raw={"tool": block.name, "input": block.input, "output": result},
                duration_ms=tool_duration_ms,
            )

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        # Append tool results for the next model turn
        messages.append({"role": "user", "content": tool_results})

    return final_text, tool_calls_this_loop, trace


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

def _verify(
    client: anthropic.Anthropic,
    user_message: str,
    agent_response: str,
    trace: ReasoningTrace,
) -> dict[str, Any]:
    """Call the verifier model and parse its JSON output.

    Args:
        client: Authenticated Anthropic client.
        user_message: Original user request.
        agent_response: Text the agent produced.
        trace: Current trace — a verify step is appended.

    Returns:
        Parsed verifier dict: {success, confidence, issues}.
    """
    tool_log = _build_tool_log(trace)
    verifier_user = (
        f"Original request: {user_message}\n\n"
        f"Tool call log:\n{tool_log}\n\n"
        f"Agent final response: {agent_response}"
    )

    t0 = time.monotonic()
    try:
        vr = client.messages.create(
            model=config.MODEL,
            max_tokens=512,
            system=VERIFIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": verifier_user}],
        )
        raw_text = vr.content[0].text if vr.content else "{}"
        result: dict[str, Any] = json.loads(_strip_code_fence(raw_text))
    except json.JSONDecodeError:
        result = {"success": True, "confidence": 0.5, "issues": ["Verifier returned non-JSON."]}
    except Exception as exc:
        logger.warning("Verifier call failed: %s", exc)
        result = {"success": True, "confidence": 0.5, "issues": [str(exc)]}

    duration_ms = (time.monotonic() - t0) * 1000
    confidence = result.get("confidence", 0.0)
    success = result.get("success", False)

    trace.add_step(
        "verify",
        f"Verifier: success={success}, confidence={confidence:.2f}",
        raw=result,
        duration_ms=duration_ms,
    )

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_plan(text: str) -> str:
    """Pull out the text inside <plan>...</plan> tags."""
    start = text.find("<plan>")
    end = text.find("</plan>")
    if start >= 0 and end > start:
        return text[start + 6 : end].strip()
    return text.strip()


def _build_tool_log(trace: ReasoningTrace) -> str:
    """Summarise all tool_call steps from the trace into a readable log string.

    Giving the verifier a concrete record of what tools ran and what they
    returned lets it assign confident scores rather than hedging at 0.5.
    """
    lines: list[str] = []
    for step in trace.steps:
        if step.phase == "tool_call" and step.raw:
            tool = step.raw.get("tool", "?")
            inp = step.raw.get("input", {})
            out = step.raw.get("output", {})
            success = out.get("success", "?")
            # Keep it terse — verifier only needs to know what ran and whether it worked
            lines.append(f"  {tool}({inp}) -> success={success}")
    return "\n".join(lines) if lines else "  (no tool calls)"


def _strip_code_fence(text: str) -> str:
    """Remove markdown code fences so json.loads() can parse the content.

    Claude sometimes wraps JSON responses in ```json ... ``` even when
    instructed not to.  This strips the fences before parsing.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Drop the opening fence line and the closing ``` line
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        return "\n".join(inner).strip()
    return stripped


def _summarise_input(inp: dict[str, Any]) -> str:
    """One-line summary of tool input for trace display."""
    parts = [f"{k}={v!r}" for k, v in inp.items()]
    summary = ", ".join(parts)
    return summary[:80] + ("…" if len(summary) > 80 else "")


def _summarise_result(result: dict[str, Any]) -> str:
    """One-line summary of tool output for trace display."""
    if result.get("success"):
        keys = [k for k in result if k not in ("success",)]
        return "✓ " + ", ".join(f"{k}={result[k]!r}" for k in keys[:3])
    return "✗ " + result.get("error", "error")
