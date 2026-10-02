# Offline win-rate benchmark

Run from the project root:

```sh
python run_full_games.py --games 10000 --workers 4 --seed 20261001
```

One game is one complete 40-card Scopa round, not a match to 11 points.
Four randomly shuffled cards start on the table; all initial tables are
accepted, with no initial king-card redeal rule. Each player receives three
cards per batch until the deck is exhausted. The engine applies mandatory
captures, matching-single-card precedence, all legal sum combinations,
Scopa (excluding the final play), and settlement of remaining table cards.
The existing ScoringEngine decides the result using all scoring categories.
Starting player alternates, giving each side 5,000 starts for 10,000 rounds.

The software uses the existing simulation greedy policy: compare **all** legal
moves using PositionEvaluator and deterministic card-ID tie breaking. This is
the depth-one DecisionEngine policy with default evaluation weights. Tests
compare its recommendations with DecisionEngine over two complete rounds.
Pending redeals are skipped in that comparison: newly dealt hands do not
change the depth-one position evaluation, an invariant covered separately.
This benchmark does not measure the default depth-two search policy.

The opponent chooses uniformly among legal moves, including separate capture
choices. Shuffling and opponent sampling use a private per-round generator
whose seed is derived from the experiment seed and round index. The software
cannot see the opponent's cards or the future deck. Worker scheduling does
not affect random streams or result ordering.

`full-game-results/rounds.csv` records every result and round seed.
`full-game-results/summary.json` records the settings, counts, mean scores,
win rates and a 95% Wilson interval. Win rate includes drawn rounds in its
denominator; decisive win rate excludes them. Confidence intervals quantify
sampling variability under this protocol, not performance against other
opponents or on a gambling website. There is no website integration.
