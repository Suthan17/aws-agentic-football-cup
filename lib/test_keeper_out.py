"""Tests for the 'opponent keeper out of goal' summary fact (run: python test_keeper_out.py)."""

import copy
import sys

from state import summarize_state, opponent_keeper_line
from test_helpers import GAME_STATE

failures = 0


def check(name, cond):
    global failures
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    failures += 0 if cond else 1


print("=== OPPONENT KEEPER ===")
gs = copy.deepcopy(GAME_STATE)  # away keeper at x=50, home attacks +x
check("keeper on his line -> in goal", opponent_keeper_line(gs["players"], 0).endswith("in goal"))
gs["players"][5]["position"] = {"x": 5, "y": 0}  # away keeper rushed to midfield
check("keeper at midfield -> OUT OF GOAL", "OUT OF GOAL" in opponent_keeper_line(gs["players"], 0))
check("summary includes the fact", "OUT OF GOAL" in summarize_state(gs, 0, 3, "FWD1"))

away = copy.deepcopy(GAME_STATE)  # we are AWAY: opponent keeper is the HOME #0 at x=-50
check("AWAY view, home keeper on line -> in goal", opponent_keeper_line(away["players"], 1).endswith("in goal"))
away["players"][0]["position"] = {"x": -10, "y": 0}
check("AWAY view, home keeper pushed up -> OUT OF GOAL", "OUT OF GOAL" in opponent_keeper_line(away["players"], 1))

srv = copy.deepcopy(GAME_STATE)  # real server scale (pitch about +/-6.4)
for p in srv["players"]:
    p["position"] = {"x": p["position"]["x"] / 7.86, "y": p["position"]["y"] / 7.86}
check("server scale, keeper on line -> in goal", opponent_keeper_line(srv["players"], 0).endswith("in goal"))
srv["players"][5]["position"] = {"x": 1.0, "y": 0}
check("server scale, keeper at x=1 -> OUT OF GOAL", "OUT OF GOAL" in opponent_keeper_line(srv["players"], 0))

kick = copy.deepcopy(GAME_STATE)  # everyone bunched near the centre
for p in kick["players"]:
    p["position"] = {"x": 0.2, "y": 0}
check("degenerate spread -> no claim", opponent_keeper_line(kick["players"], 0) == "")

print(f"\n{'All' if not failures else failures} tests {'passed' if not failures else 'FAILED'}")
sys.exit(1 if failures else 0)
