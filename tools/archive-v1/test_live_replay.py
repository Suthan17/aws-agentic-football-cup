"""Real Bedrock calls on real recorded ticks (no stub): sanity + latency."""
import asyncio
import importlib.util
import json
import sys
import time

ROOT = r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents"
sys.path.insert(0, ROOT + r"\lib")
from test_helpers import mock_agentcore  # noqa: E402

mock_agentcore()
captured = {}


class App:
    class logger:
        info = staticmethod(lambda m: print("    log:", m[:150]) if any(k in m for k in ("RULE", "GUARD", "LLM returned", "ERROR", "fallback")) else None)
        warn = info
        error = staticmethod(lambda m: print("    ERROR:", m[:200]))

    def entrypoint(self, fn):
        captured["fn"] = fn
        return fn

    def run(self):
        pass


sys.modules["bedrock_agentcore.runtime"].BedrockAgentCoreApp = App
handlers = {}
for folder, pid in [("ai-def", 1), ("ai-mid", 2), ("ai-fwd1", 3), ("ai-fwd2", 4)]:
    spec = importlib.util.spec_from_file_location(folder, rf"{ROOT}\ai-team-strands-balanced\{folder}\src\main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    handlers[pid] = captured["fn"]

rows = [json.loads(l)["payload"] for l in open(r"C:\dev\tools\replay_tau.jsonl", encoding="utf-8")]
rows = [r for r in rows if len(r["gameState"].get("players", [])) == 10]
picks = [r for r in rows if 80 < r["gameState"]["gameTime"] < 82][:1] + rows[20:21] + rows[45:46]


async def call(fn, payload):
    return [c async for c in fn(payload, None)]

for r in picks:
    gs = r["gameState"]
    b = gs["ball"]["position"]
    print(f"\n== t={gs['gameTime']:.0f}s ball=({b['x']:.2f},{b['z']:.2f}) holder={gs['ball'].get('possessionAgentId')} free={gs['ball'].get('isFree')}")
    for pid, fn in handlers.items():
        t0 = time.time()
        out = asyncio.run(call(fn, {"prompt": json.dumps({"gameState": gs, "teamId": 0, "myPlayers": [pid]})}))
        print(f"  p{pid}: {out[0]}  ({time.time() - t0:.2f}s)")
