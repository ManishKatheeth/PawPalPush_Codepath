"""
PawPal+ Agent Evaluation Harness.

Usage:
    python -m eval.harness

For each scenario in eval/scenarios.py:
  1. Spins up a fresh fixture owner (or empty owner for edge cases).
  2. Runs the agent with the scenario request.
  3. Scores the result against expected criteria.
  4. Prints a summary table and saves results to eval/results/run_<timestamp>.json.

This script IS allowed to make real Anthropic API calls — it is the integration
test layer. The unit tests in tests/ mock the API.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path when run as `python -m eval.harness`
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

from agent.core import run_agent
from agent.trace import ReasoningTrace
from eval.scenarios import SCENARIOS, Scenario, make_empty_owner, make_fixture_owner


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_scenario(scenario: Scenario, trace: ReasoningTrace) -> dict:
    """Evaluate a trace against a scenario's expected criteria.

    Args:
        scenario: The scenario definition with expectations.
        trace: The trace produced by running the agent.

    Returns:
        A dict with keys: pass, reasons, tools_called, expected_tools_match,
        forbidden_tools_hit, confidence, state_check_passed.
    """
    reasons: list[str] = []

    # Collect tools actually called
    tools_called: list[str] = []
    for step in trace.steps:
        if step.phase == "tool_call" and step.raw:
            tool_name = step.raw.get("tool", "")
            if tool_name:
                tools_called.append(tool_name)

    # Check expected tools
    missing_tools = [t for t in scenario.expected_tools if t not in tools_called]
    expected_tools_match = len(missing_tools) == 0
    if missing_tools:
        reasons.append(f"Expected tools not called: {missing_tools}")

    # Check forbidden tools
    forbidden_hit = [t for t in scenario.forbidden_tools if t in tools_called]
    if forbidden_hit:
        reasons.append(f"Forbidden tools were called: {forbidden_hit}")

    # Confidence
    confidence = trace.verifier_result.get("confidence", 0.0)

    # State check
    state_check_passed: bool | None = None
    if scenario.expected_state_check is not None:
        try:
            state_check_passed = scenario.expected_state_check(
                # The executor mutates the owner in-place; access it via the trace request
                # We can't re-access the owner here easily, so we track via trace closure.
                # This is set by the harness runner below.
                _owner_ref[0]  # type: ignore[name-defined]
            )
        except Exception as exc:
            state_check_passed = False
            reasons.append(f"State check raised: {exc}")
        if state_check_passed is False:
            reasons.append("Post-state assertion failed.")

    # Clarification check — if scenario expects a question, look for "?" in response
    if scenario.should_ask_clarification:
        if "?" not in trace.final_response:
            reasons.append("Expected a clarifying question but none found in response.")

    # Refusal check
    if scenario.should_refuse:
        refusal_indicators = ["i can't", "i cannot", "i'm unable", "redirect", "pet care"]
        lowered = trace.final_response.lower()
        if not any(ind in lowered for ind in refusal_indicators):
            reasons.append("Expected a redirect/refusal but response seems compliant.")

    passed = (
        expected_tools_match
        and not forbidden_hit
        and not reasons
    )

    return {
        "pass": passed,
        "reasons": reasons,
        "tools_called": tools_called,
        "expected_tools_match": expected_tools_match,
        "forbidden_tools_hit": forbidden_hit,
        "confidence": confidence,
        "state_check_passed": state_check_passed,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_harness() -> None:
    """Execute all scenarios and print a summary table."""
    results = []
    passed_count = 0
    total_confidence = 0.0

    print("\n" + "=" * 80)
    print("PawPal+ Agent Evaluation Harness")
    print(f"Running {len(SCENARIOS)} scenarios  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    for scenario in SCENARIOS:
        global _owner_ref
        owner = make_empty_owner() if scenario.id == "edge_no_pets" else make_fixture_owner()
        _owner_ref = [owner]  # mutable cell so score_scenario can reach it

        print(f"\n[{scenario.difficulty.upper()}] {scenario.id}")
        print(f"  Request: {scenario.request[:80]}{'…' if len(scenario.request) > 80 else ''}")

        t0 = time.monotonic()
        try:
            trace = run_agent(scenario.request, owner, persist=False)
        except Exception as exc:
            trace = _error_trace(scenario.request, str(exc))
            print(f"  ERROR during agent run: {exc}")

        elapsed = time.monotonic() - t0

        score = score_scenario(scenario, trace)
        verdict = "PASS ✓" if score["pass"] else "FAIL ✗"

        print(f"  Tools called : {score['tools_called']}")
        print(f"  Expected match: {score['expected_tools_match']}  |  "
              f"Confidence: {score['confidence']:.2f}  |  "
              f"Elapsed: {elapsed:.1f}s  |  {verdict}")

        if score["reasons"]:
            for r in score["reasons"]:
                print(f"  ⚠  {r}")

        if score["pass"]:
            passed_count += 1
        total_confidence += score["confidence"]

        results.append({
            "scenario_id": scenario.id,
            "description": scenario.description,
            "difficulty": scenario.difficulty,
            "request": scenario.request,
            "tools_called": score["tools_called"],
            "expected_tools_match": score["expected_tools_match"],
            "forbidden_tools_hit": score["forbidden_tools_hit"],
            "confidence": score["confidence"],
            "state_check_passed": score["state_check_passed"],
            "pass": score["pass"],
            "reasons": score["reasons"],
            "elapsed_s": round(elapsed, 2),
            "final_response_snippet": trace.final_response[:200],
            "trace_steps": len(trace.steps),
            "total_tool_calls": trace.total_tool_calls,
            "iterations": trace.iterations,
        })

    # Summary
    n = len(SCENARIOS)
    mean_conf = total_confidence / n if n else 0.0

    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed_count}/{n} scenarios passed  |  mean confidence: {mean_conf:.2f}")
    print("=" * 80 + "\n")

    # Save results
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_dir = _PROJECT_ROOT / "eval" / "results"
    results_dir.mkdir(exist_ok=True)
    out_path = results_dir / f"run_{ts}.json"
    out_path.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "passed": passed_count,
                "total": n,
                "mean_confidence": round(mean_conf, 4),
                "scenarios": results,
            },
            indent=2,
        )
    )
    print(f"Full results saved to: {out_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_owner_ref: list = []  # module-level mutable cell for owner access in score_scenario


def _error_trace(request: str, error: str) -> ReasoningTrace:
    """Return a minimal failed trace for when the agent crashes."""
    from agent.trace import ReasoningTrace
    trace = ReasoningTrace(request=request)
    trace.add_step("final", f"ERROR: {error}")
    trace.finish(f"ERROR: {error}", {"success": False, "confidence": 0.0, "issues": [error]})
    return trace


if __name__ == "__main__":
    run_harness()
