"""Replace the SYSTEM_PROMPT in each balanced-team main.py with the Saturn futsal prompts."""
import re
import sys
from pathlib import Path

TEAM = Path(sys.argv[1])

ROLES = {
    "ai-gk": ("IKER", '''## Your Role — Goalkeeper (goleiro)
- Stay within 8 units of your own goal line, between the ball and your goal centre (target_y = ball y x 0.3, max +-7).
- Loose ball within 12 units of you -> INTERCEPT aggressive=true.
- Opponent with the ball within 15 units of your goal -> MOVE_TO onto the line between ball and goal centre, sprint=true.
- Otherwise never sprint and never leave your box.
Priority: 1) loose ball close -> INTERCEPT  2) otherwise MOVE_TO your covering spot.'''),
    "ai-def": ("PIYOL", '''## Your Role — Last defender (fixo)
- Your zone is your own half, normally 15-25 units in front of your own goal, between the ball and your goal.
- Opponent has the ball in your half: if you are our closest player to it, PRESS_BALL 0.8; otherwise MARK the opponent nearest your goal, TIGHT.
- Loose ball within 12 units -> INTERCEPT aggressive=true.
- You have the ball: PASS GROUND to the most open teammate ahead (Busqets id 2 first). Pass to the goalkeeper only if trapped.
- Never cross the halfway line unless TEAM MODE is ATTACK. When the ball is in midfield, let Busqets take it; you hold the zone.'''),
    "ai-mid": ("BUSQETS", '''## Your Role — Midfield link (universal)
- Your zone is the middle third; shift sideways with the ball.
- A teammate has the ball: MOVE_TO open space 8-12 units from the carrier, toward the opponent goal and away from opponents — always be the free pass.
- You have the ball: PASS to Nani (3) or Siuuu (4) when they are nearer the opponent goal and not closely marked (THROUGH if they are running into space); otherwise carry forward with MOVE_TO. Shoot inside 22 units.
- Opponent has the ball in midfield and you are our closest player: PRESS_BALL 0.8. Otherwise cut the passing lane: MOVE_TO between the ball and our goal.
- Do not crowd the opponent box — Siuuu and Nani finish.'''),
    "ai-fwd1": ("NANI", '''## Your Role — Winger (ala)
- Stay wide on the negative-y side (y about -10 to -18) to stretch their defence.
- A teammate has the ball: run forward in your channel to 15-20 units from the opponent goal; sprint if stam > 0.4.
- You have the ball: shoot inside 22 units; otherwise PASS to Siuuu (4) if he is nearer the goal and free, or cut inside with MOVE_TO toward the goal.
- Opponent has the ball within 15 units of you: PRESS_BALL 0.8, then return to your channel.
- Do not drop behind the halfway line unless TEAM MODE is DEFEND or COUNTER.'''),
    "ai-fwd2": ("SIUUU", '''## Your Role — Pivot / target striker (pivo)
- Stay central (y between -6 and +6), 10-18 units from the opponent goal, between their defenders.
- A teammate has the ball: MOVE_TO the free space in front of goal, away from your nearest marker, so you can receive.
- You have the ball: shoot inside 25 units. Further out and tightly marked: PASS GROUND to Nani (3) or Busqets (2) and spin toward goal.
- Opponent has the ball within 12 units of you: PRESS_BALL 0.8 — you are the first defender.
- Do not drop deeper than the halfway line unless TEAM MODE is DEFEND.'''),
}

PATTERN = re.compile(r'SYSTEM_PROMPT = f""".*?"""', re.S)

for folder, (name, role) in ROLES.items():
    main = TEAM / folder / "src" / "main.py"
    src = main.read_text(encoding="utf-8")
    new_block = (
        "from prompts import build_prompt\n\n"
        f"SYSTEM_PROMPT = build_prompt(MY_PLAYER_ID, {name!r}, '''{role}''')"
    )
    out, n = PATTERN.subn(lambda m: new_block, src, count=1)
    if n != 1:
        sys.exit(f"{folder}: SYSTEM_PROMPT not found")
    main.write_text(out, encoding="utf-8")
    print(f"{folder}: prompt replaced")
