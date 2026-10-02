# Three-player offline benchmark

Run `python run_three_player_games.py` from the project root.
Three independent players, with no partnerships, play a complete 40-card
round: four initial table cards, three cards per hand, four batches and
36 plays. All initial tables are accepted, as in the two-player benchmark.
The starting seat rotates by round index modulo three; these sample sizes
are not divisible by three, so start counts differ by at most one.

The standard capture combinations and single-card priority reuse RulesEngine.
Primiera values reuse calculate_primiera and ScoringConfig. The final table
belongs to the last capturer; a sweep on the final play earns no Scopa.
Each scoring category goes to its unique leader among three players, with
no point for a tied category. Primiera requires all four suits. The three
players' cards remain separate throughout the round.

The original two-player GameState/DecisionEngine is unchanged. This separate
simulator extends its depth-one evaluation approach: compare all legal moves,
using own public utility minus the greatest rival utility, then stable card-ID
tie breaking. Evaluation considers captures, Denari, Scopa, Sette Bello and
Primiera. It does not search opponent replies and is not the original
two-player DecisionEngine running with an invented second opponent.
The policy sees public captures and its legal actions, not private opponent
card identities or future draw cards. Both opponents independently select a
uniform legal move; they do not cooperate.

Win = sole highest round score; draw = shared highest score including the
software; loss = software below the highest score, including tied second.
This is a round benchmark, not a multi-round match to eleven points.

Seed is 20261001. Each round derives its own RNG seed from its index, so
parallel scheduling cannot alter results. The 100, 200, 500 and 1000 reports
are prefixes of the 10000-round simulation, not independent samples.
All five sizes receive separate CSV and JSON reports under
`three-player-results`. Each interval is a 95% Wilson interval for the
proportion of sole first-place finishes.

Reference for the individual three-player format:
https://www.pagat.com/fishing/scopa.html
This configurable experiment uses the existing engine's scoring conventions;
it does not claim compatibility with any particular third-party platform.
