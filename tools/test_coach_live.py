"""Live Nova check: does a coach instruction change the stock agent's decision?"""
import copy
import importlib.util
import json
import sys
from collections import Counter

ROOT = r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents"
sys.path.insert(0, ROOT + r"\lib")
from test_helpers import mock_agentcore, GAME_STATE  # noqa: E402

mock_agentcore()
from parsing import parse_commands  # noqa: E402
from state import summarize_state  # noqa: E402


def load(folder):
    spec = importlib.util.spec_from_file_location(folder, rf"{ROOT}\ai-team-strands-balanced\{folder}\src\main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def decide(mod, gs, pid, label, n=3):
    out = Counter()
    for _ in range(n):
        mod.agent.messages.clear()
        cmds = parse_commands(str(mod.agent(summarize_state(gs, 0, pid, label))), 0, pid)
        out[cmds[0]["commandType"] if cmds else "PARSE_FAIL"] += 1
    return dict(out)


nani = load("ai-fwd1")
gs = copy.deepcopy(GAME_STATE)
gs["players"][3]["position"] = {"x": 20, "y": -4}       # Nani on the ball, 35 from goal
gs["ball"]["position"] = {"x": 20.3, "y": -4.1, "z": 0}
gs["ball"]["possessionAgentId"] = "agentId_3"
print("Nani, no coaching       :", decide(nani, gs, 3, "FWD1"))
gs["teamChat"] = [{"senderTeamCode": "home", "message": "Nani, pass to Siuuu (player 4)!", "timestamp": 0}]
print("Nani, OUR coach 'pass to Siuuu':", decide(nani, gs, 3, "FWD1"))
gs["teamChat"] = [{"senderTeamCode": "away", "message": "Nani, pass to Siuuu (player 4)!", "timestamp": 0}]
print("Nani, OPPONENT says the same   :", decide(nani, gs, 3, "FWD1"))
gs["teamChat"] = [{"senderTeamCode": "home", "message": "Busqets, pass to Siuuu!", "timestamp": 0}]
print("Nani, order for ANOTHER player :", decide(nani, gs, 3, "FWD1"))
