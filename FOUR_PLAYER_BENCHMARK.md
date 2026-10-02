# Four-player free-for-all benchmark

Run `python run_four_player_games.py` from the project root.

This offline variant uses four independent players, without partnerships.
Seat 0 is the software; seats 1, 2 and 3 independently select a uniformly
random legal move, including capture choices. Each round uses the standard
40-card deck, four initial table cards, three cards per hand, three dealing
batches and 36 plays. All initial tables are accepted. Starter rotates
through all four seats; all requested sample sizes have balanced starts.

The shared multiplayer rules use the existing capture combination engine,
single-card priority and mandatory capture. Sweeping the table is Scopa
except on the final play. Remaining table cards go to the last capturer.
Scoring is individual: captured cards, Denari and eligible Primiera award
one point to the unique category leader; ties award no point. Sette Bello
and Scopa are scored independently for each seat. No scores are pooled.

The software compares all legal moves using a depth-one public evaluation:
its own utility minus the greatest of the three rival utilities. It includes
captured cards, Scopa, Denari, Sette Bello and Primiera, with default weights
and deterministic tie-breaking. It has no knowledge of opponents' private
card identities or the future draw order. This is a multiplayer heuristic,
not the original two-player DecisionEngine's default search.

A win means sole first place by final round points. A draw means shared
first place including the software. Any lower position is a loss, including
tied second place. One game here means a complete round, not a match to a
target score or a third-party site's game.

Seed: 20261001; four worker processes. Each round has an index-derived seed.
Smaller samples (100, 200, 500 and 1000) are prefixes of the 10000-round
simulation, not independent experiments. JSON and CSV results are saved in
`four-player-results`. The reported win-rate interval is a 95% Wilson interval.
Existing three-player interfaces remain available through compatibility
exports; the two-player GameState and DecisionEngine are unchanged.
