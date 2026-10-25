"""End-to-end: call each agent's real invoke handler with a sample payload."""
import asyncio
import copy
import importlib.util
import json
import sys
import time

ROOT = r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents"
sys.path.insert(0, ROOT + r"\lib")
from test_helpers import mock_agentcore, GAME_STATE  # noqa: E402

mock_agentcore()

captured = {}


class App:
    class logger:
        info = staticmethod(lambda m: print("    log:", m[:160]))
        warn = info
        error = info

    def entrypoint(self, fn):
        captured["fn"] = fn
        return fn

    def run(self):
        pass


sys.modules["bedrock_agentcore.runtime"].BedrockAgentCoreApp = App


async def call(fn, payload):
    return [chunk async for chunk in fn(payload, None)]


for folder, pid in [("ai-gk", 0), ("ai-def", 1), ("ai-mid", 2), ("ai-fwd1", 3), ("ai-fwd2", 4)]:
    spec = importlib.util.spec_from_file_location(folder, rf"{ROOT}\ai-team-strands-balanced\{folder}\src\main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    gs = copy.deepcopy(GAME_STATE)
    gs["teamChat"] = ["nani shoot", "sf attack"]
    payload = {"prompt": json.dumps({"gameState": gs, "teamId": 0, "myPlayers": [pid]})}
    for attempt in ("cold", "warm", "warm"):
        t0 = time.time()
        out = asyncio.run(call(captured["fn"], payload))
        print(f"== {folder} [{attempt}]: {out[0][:90]}  ({time.time() - t0:.2f}s)")
