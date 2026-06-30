#!/usr/bin/env bash
# specopt-mcp install script (Unix)
# Two-step install to work around DSPy's pin of gepa==0.0.27:
#   Step 1 installs everything including DSPy (which pulls gepa==0.0.27 transitively).
#   Step 2 overrides with gepa>=0.1.1 so optimize_anything is available.

set -euo pipefail

echo "=== Step 1/2: Installing specopt-server + DSPy ==="
pip install -e .

echo "=== Step 2/2: Upgrading gepa to >=0.1.1 (overriding DSPy's pin) ==="
pip install 'gepa>=0.1.1,<0.2' --force-reinstall --no-deps

echo "=== Done! ==="
echo "Run 'python agent_brain.py' to start the agent."
