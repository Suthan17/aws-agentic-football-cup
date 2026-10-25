"""Replay regression test: real match payloads through the real invoke handler.

Every recorded tick is sent to all 5 agents (as both HOME and AWAY), with the
LLM replaced by a stub that cycles through good and bad commands. Checks the
invariants that matter on the real (small) server pitch.
"""
import asyncio
import glob
import importlib.util
import itertools
import json
import math
import sys

ROOT = r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents"
sys.path.insert(0, ROOT + r"\lib")
from test_helpers import mock_agentcore  # noqa: E402

mock_agentcore()
import agent_base  # noqa: E402
import frame  # noqa: E402
from state import _resolve_holder  # noqa: E402

STUB_OUTPUTS = itertools.cycle([
    '[{"commandType":"MOVE_TO","playerId":9,"parameters":{"target_x":40.0,"target_y":-20.0,"sprint":true},"duration":0}]',
    '[{"commandType":"SHOOT","playerId":9,"parameters":{"aim_location":"TR","power":0.5},"duration":0}]',
    '[{"commandType":"RESET","playerId":9,"parameters":{},"duration":0}]',
    '[{"commandType":"PASS","playerId":9,"parameters":{"target_player_id":2,"type":"GROUND"},"duration":0}]',
    '[{"commandType":"SLIDE_TACKLE","playerId":9,"parameters":{"target_player_id":1,"sprint":true,"distance":5},"duration":0}]',
    '[{"commandType":"PRESS_BALL","playerId":9,"parameters":{"intensity":1.0},"duration":3}]',
    'not json at all',
    '[{"commandType":"MOVE_TO","playerId":9,"parameters":{"target_x":-60,"target_y":50,"sprint":true},"duration":0}]',
])


class StubAgent:
    def __init__(self):
        self.messages = []

    def __call__(self, prompt):
        assert "Your goal at x=" in prompt
        return next(STUB_OUTPUTS)


agent_base.create_agent = lambda *a, **k: StubAgent()
if "--mutate" in sys.argv:  # prove the test catches the v1.2 behaviour (no frame adapter)
    agent_base.is_server_frame = lambda gs: False
    agent_base.to_canonical = lambda gs: gs
captured = {}


class App:
    class logger:
        lines = []
        info = staticmethod(lambda m: App.logger.lines.append(m))
        warn = info
        error = staticmethod(lambda m: App.logger.lines.append("ERROR " + m))

    def entrypoint(self, fn):
        captured["fn"] = fn
        return fn

    def run(self):
        pass


sys.modules["bedrock_agentcore.runtime"].BedrockAgentCoreApp = App

handlers = {}
for folder, pid in [("ai-gk", 0), ("ai-def", 1), ("ai-mid", 2), ("ai-fwd1", 3), ("ai-fwd2", 4)]:
    spec = importlib.util.spec_from_file_location(folder, rf"{ROOT}\ai-team-strands-balanced\{folder}\src\main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    handlers[pid] = captured["fn"]


async def call(fn, payload):
    return [c async for c in fn(payload, None)]


payloads = []
for f in glob.glob(r"C:\dev\tools\replay_*.jsonl"):
    for line in open(f, encoding="utf-8"):
        p = json.loads(line)["payload"]
        if len(p.get("gameState", {}).get("players", [])) == 10:
            payloads.append(p)

fails = []


def fail(msg):
    if len(fails) < 15:
        print("  [FAIL]", msg)
    fails.append(msg)


ticks = holder_checks = holder_far = 0
for p in payloads:
    gs = p["gameState"]
    canon = frame.to_canonical(gs)
    # Frame conversion: ball width must come from z; all canonical x within the documented pitch.
    if not frame.is_server_frame(gs):
        fail("recorded payload not detected as server frame")
    b = gs["ball"]["position"]
    cb = canon["ball"]["position"]
    if abs(cb["y"] - b["z"] * frame.S) > 1e-6:
        fail("ball width not taken from z")
    h = _resolve_holder(canon["ball"], canon["players"])
    if h is not None and canon["ball"].get("isFree") is not True:
        holder_checks += 1
        dd = math.hypot(h["position"]["x"] - cb["x"], h["position"]["y"] - cb["y"])
        if dd > 1.5 * frame.S:   # 1.5 server units
            holder_far += 1
    for team in (0, 1):
        my_goal_raw = -frame.SERVER_GOAL_X if team == 0 else frame.SERVER_GOAL_X
        for pid, fn in handlers.items():
            ticks += 1
            payload = {"prompt": json.dumps({"gameState": gs, "teamId": team, "myPlayers": [pid]})}
            try:
                out = json.loads(asyncio.run(call(fn, payload))[0])
            except Exception as e:  # noqa: BLE001
                fail(f"pid {pid} team {team} crashed: {e}")
                continue
            if not out:
                fail(f"pid {pid} returned no command")
            for c in out:
                t, prm = c.get("commandType"), c.get("parameters", {})
                if c.get("playerId") != pid:
                    fail(f"pid {pid}: command for player {c.get('playerId')}")
                if t in ("RESET", "CLEAR_OVERRIDE", "SLIDE_TACKLE"):
                    fail(f"pid {pid}: banned {t} reached the server")
                if t == "MOVE_TO":
                    tx, ty = prm.get("target_x"), prm.get("target_y")
                    if abs(tx) > frame.SERVER_MAX_X + 1e-6 or abs(ty) > frame.SERVER_MAX_Y + 1e-6:
                        fail(f"pid {pid}: MOVE_TO off the real pitch ({tx},{ty})")
                    if pid == 0 and abs(tx - my_goal_raw) > 1.8:
                        fail(f"GK team {team}: MOVE_TO {tx:.2f} too far from own goal line {my_goal_raw}")
errors = [l for l in App.logger.lines if l.startswith("ERROR")]
for e in errors[:5]:
    fail(e[:200])

print(f"payloads={len(payloads)} agent-ticks={ticks} holder-checks={holder_checks} holder>1.5u from ball={holder_far}")
if holder_checks and holder_far / holder_checks > 0.05:
    fail(f"possession resolver picks a player far from the ball in {holder_far}/{holder_checks} ticks")
if not payloads:
    fail("no replay payloads found")
print("\nALL PASS" if not fails else f"\nSOME FAILED ({len(fails)})")
sys.exit(0 if not fails else 1)
