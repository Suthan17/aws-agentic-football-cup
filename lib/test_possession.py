"""Possession with ambiguous agentIds (run: python test_possession.py)."""

import copy
import sys

from state import holder_is_me, get_possession_info, summarize_state
from test_helpers import GAME_STATE

failures = 0


def check(name, cond):
    global failures
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    failures += 0 if cond else 1


print("=== POSSESSION: same agentId on both teams ===")
gs = copy.deepcopy(GAME_STATE)
# Opponent #4 (away) carries the ball deep in the home half; our #4 is upfield.
gs["players"][9]["position"] = {"x": -25, "y": 3}
gs["ball"]["position"] = {"x": -24.7, "y": 3.1, "z": 0}
gs["ball"]["possessionAgentId"] = "agentId_4"
check("HOME #4 does not 'have' the opponent's ball", not holder_is_me(gs["ball"], gs["players"], 0, 4))
check("HOME sees opponent possession", get_possession_info(gs["ball"], gs["players"], 0)[2] is False)
check("summary tells our #4 hasBall=False", "hasBall=False" in summarize_state(gs, 0, 4, "FWD2"))
check("AWAY #4 does have it", holder_is_me(gs["ball"], gs["players"], 1, 4))

gs2 = copy.deepcopy(GAME_STATE)  # our #3 at x=14 carries the ball (stock fixture)
gs2["ball"]["position"] = {"x": 14.2, "y": -5.1, "z": 0}
check("HOME #3 on the ball has it", holder_is_me(gs2["ball"], gs2["players"], 0, 3))

# Server frame: small pitch, ball width on z, height on y.
srv = copy.deepcopy(GAME_STATE)
for p in srv["players"]:
    p["position"] = {"x": p["position"]["x"] / 7.86, "y": p["position"]["y"] / 7.86}
srv["players"][9]["position"] = {"x": -3.2, "y": 0.4}
srv["ball"]["position"] = {"x": -3.15, "y": 0.14, "z": 0.38}
srv["ball"]["possessionAgentId"] = "agentId_4"
check("server frame: opponent carrier resolved correctly", not holder_is_me(srv["ball"], srv["players"], 0, 4))

print(f"\n{'All' if not failures else failures} tests {'passed' if not failures else 'FAILED'}")
sys.exit(1 if failures else 0)
