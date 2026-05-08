#!/usr/bin/env python3
"""Compatibility launcher for the packaged proxy app.

Preferred usage:
  uv run ollama-proxy
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ollama_proxy.cli import main


if __name__ == "__main__":
    main()
