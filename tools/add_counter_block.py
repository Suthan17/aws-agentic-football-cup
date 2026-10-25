"""Insert the counter-attack strategy block into each counter-squad prompt.

AWS format: identity line -> capability/strategy block -> ## Your Role -> ...
(same place the Memory team puts its "You have MEMORY..." block). Prompt-only.
"""
import pathlib
import sys

TEAM = pathlib.Path(r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents\ai-team-saturn-counter")

COMMON = (
    "## Match Plan — Counter-Attack (vs teams that push everyone forward)\n"
    "- The state tells you if the opponent goalkeeper is OUT OF GOAL. Their keeper often leaves the net empty.\n"
)
BLOCKS = {
    "ai-gk": COMMON + (
        "- Their keeper and defender run at our goal: stay on your line between ball and goal centre, never come out to meet them.\n"
        "- When you have the ball and their keeper is OUT OF GOAL: GK_DISTRIBUTE with KICK to the forward nearest their goal.\n"
    ),
    "ai-def": COMMON + (
        "- Never leave our half while they have the ball. MARK (TIGHT) the opponent closest to our goal — including their goalkeeper if he is attacking.\n"
        "- When you win the ball: PASS type THROUGH straight to the forward nearest their goal. Do not dribble.\n"
    ),
    "ai-mid": COMMON + (
        "- When they have the ball: drop between the ball and our goal and INTERCEPT.\n"
        "- When we win the ball: THROUGH pass to the most advanced forward at once.\n"
        "- If you have the ball, are in their half and their keeper is OUT OF GOAL: SHOOT immediately.\n"
    ),
    "ai-fwd1": COMMON + (
        "- Stay high in their half when they attack — you are the outlet for the counter.\n"
        "- If you have the ball and their keeper is OUT OF GOAL: SHOOT immediately from anywhere in their half.\n"
    ),
    "ai-fwd2": COMMON + (
        "- Stay high in their half when they attack — you are the outlet for the counter.\n"
        "- If you have the ball and their keeper is OUT OF GOAL: SHOOT immediately from anywhere in their half.\n"
    ),
}

for folder, block in BLOCKS.items():
    main = TEAM / folder / "src" / "main.py"
    src = main.read_text(encoding="utf-8")
    if "## Match Plan" in src:
        print(f"{folder}: already has the block")
        continue
    anchor = "\n\n## Your Role"
    if src.count(anchor) != 1:
        sys.exit(f"{folder}: expected exactly one '## Your Role' section")
    main.write_text(src.replace(anchor, "\n\n" + block.rstrip("\n") + anchor, 1), encoding="utf-8")
    print(f"{folder}: block inserted")
