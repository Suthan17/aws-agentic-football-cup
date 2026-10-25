"""Prompt-only experiments safety check: each agent module imports, its prompt
names its own player id, lists the response format, and stays short enough
for the latency budget."""
import importlib.util
import sys

import os

ROOT = r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents"
TEAM = os.environ.get("SATURN_TEAM", "ai-team-strands-balanced")
sys.path.insert(0, ROOT + r"\lib")
from test_helpers import mock_agentcore  # noqa: E402

mock_agentcore()
import agent_base  # noqa: E402

agent_base.create_agent = lambda *a, **k: object()  # no Bedrock client needed
ok = True
for folder, pid in [("ai-gk", 0), ("ai-def", 1), ("ai-mid", 2), ("ai-fwd1", 3), ("ai-fwd2", 4)]:
    spec = importlib.util.spec_from_file_location(folder, rf"{ROOT}\{TEAM}\{folder}\src\main.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001
        print(f"  [FAIL] {folder}: import error {e}")
        ok = False
        continue
    p = mod.SYSTEM_PROMPT
    checks = {
        "MY_PLAYER_ID matches folder": mod.MY_PLAYER_ID == pid,
        f"prompt names player {pid}": f"player {pid}" in p,
        "prompt asks for a JSON array": "JSON array" in p,
        "prompt under 6000 chars": len(p) < 6000,
    }
    for name, good in checks.items():
        print(f"  [{'PASS' if good else 'FAIL'}] {folder}: {name} ({len(p)} chars)" if name.startswith("prompt under") else
              f"  [{'PASS' if good else 'FAIL'}] {folder}: {name}")
        ok &= good
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
