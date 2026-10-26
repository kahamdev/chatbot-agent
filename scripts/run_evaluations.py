#!/usr/bin/env python3
"""Run the local evaluation cases. Exits with the number of failures."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatbot_agent.evals import run

if __name__ == "__main__":
    sys.exit(run())
