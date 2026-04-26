"""
Agent configuration constants.
All tunable knobs live here — never hardcoded in logic files.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-6"
TEMPERATURE = 1.0        # Claude tool-use works best at default temp
MAX_TOKENS = 4096

# ---------------------------------------------------------------------------
# Agent loop limits
# ---------------------------------------------------------------------------
MAX_ITERATIONS = 8                     # hard cap on plan/replan cycles
MAX_TOOL_CALLS = 20                    # abort if a single turn exceeds this
REPLAN_CONFIDENCE_THRESHOLD = 0.7     # replan when verifier confidence < this
MAX_REPLAN_ATTEMPTS = 2

# ---------------------------------------------------------------------------
# Input / output limits
# ---------------------------------------------------------------------------
MAX_INPUT_CHARS = 2000

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "agent.log"
LOG_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# API key — loaded from env (use python-dotenv in entry points)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
