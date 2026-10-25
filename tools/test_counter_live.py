"""Live Nova check of the counter squad on Total-Attack-style situations."""
import copy
import importlib.util
import sys
from collections import Counter

ROOT = r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents"
TEAM = sys.argv[1] if len(sys.argv) > 1 else "ai-team-saturn-counter"
sys.path.insert(0, ROOT + r"\lib")
from test_helpers import mock_agentcore, GAME_STATE  # noqa: E402

mock_agentcore()
from parsing import parse_commands  # noqa: E402
from state import summarize_state  # noqa: E402

mods = {}


def agent(folder):
    if folder not in mods:
        spec = importlib.util.spec_from_file_location(folder, rf"{ROOT}\{TEAM}\{folder}\src\main.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mods[folder] = m
    return mods[folder]


def run(label, folder, pid, role, gs, n=3):
    m, out = agent(folder), Counter()
    for _ in range(n):
        m.agent.messages.clear()
        cmds = parse_commands(str(m.agent(summarize_state(gs, 0, pid, role))), 0, pid)
        c = cmds[0] if cmds else {}
        key = c.get("commandType", "PARSE_FAIL")
        if key == "GK_DISTRIBUTE":
            key += "/" + str(c.get("parameters", {}).get("method"))
        out[key] += 1
    print(f"RESULT {label:55s} {dict(out)}")


base = copy.deepcopy(GAME_STATE)
keeper_out = copy.deepcopy(base)
keeper_out["players"][5]["position"] = {"x": 5, "y": 0}          # their keeper at midfield

s = copy.deepcopy(keeper_out)                                      # Nani on the ball, 35 out, empty net
s["players"][3]["position"] = {"x": 20, "y": -4}
s["ball"].update(position={"x": 20.3, "y": -4.1, "z": 0}, possessionAgentId="agentId_3")
run("Nani has ball 35 out, their keeper OUT", "ai-fwd1", 3, "FWD1", s)

s = copy.deepcopy(keeper_out)                                      # Busqets on the ball in their half
s["players"][2]["position"] = {"x": 12, "y": 2}
s["ball"].update(position={"x": 12.2, "y": 2.0, "z": 0}, possessionAgentId="agentId_2")
run("Busqets has ball in their half, keeper OUT", "ai-mid", 2, "MID", s)

s = copy.deepcopy(keeper_out)                                      # their keeper dribbling at our goal
s["players"][5]["position"] = {"x": -30, "y": 2}
s["ball"].update(position={"x": -30.2, "y": 2.0, "z": 0}, possessionAgentId="agentId_0")
run("Piyol: their KEEPER carries ball in our half", "ai-def", 1, "DEF", s)

s = copy.deepcopy(keeper_out)                                      # Iker holds it, their net empty
s["ball"].update(position={"x": -49.8, "y": 0.1, "z": 0}, possessionAgentId="agentId_0")
run("Iker has ball, their keeper OUT", "ai-gk", 0, "GK", s)
