# Scopa — engine and FastAPI

## Offline observation adapter

`site_adapter/betsson` contains a read-only mock observation boundary for synthetic
training data. It converts explicit fixtures to the standard GameState and delegates
analysis to the unchanged DecisionEngine. Source status is kept outside GameState.
It is not a live Betsson.it integration or a verified site payload format; it has
no network, browser, login or move-execution capabilities. See
[adapter documentation](site_adapter/betsson/README.md) for the format and tests.

## Docker Compose

With Docker Desktop running in Linux-container mode, run from this directory:

```sh
docker compose up --build -d
docker compose ps
docker compose logs backend
docker compose down
```

API documentation: http://127.0.0.1:8000/docs. Set BACKEND_PORT in `.env` to
change the local port. Compose currently runs the implemented backend only.
The backend healthcheck requests OpenAPI; it uses one Uvicorn application worker
because game storage is in memory. Data is lost when the container restarts.

Implemented: configurable card universe, immutable cards and deck operations,
validated immutable player-information state, capture combinations, legal move
generation, rules-based state transitions, modular scoring, hidden-card probabilities
and a configurable belief-state game tree with a Decision Engine, reproducible
parallel Monte Carlo simulation and FastAPI endpoints.
Python 3.12+; the engine itself has no runtime dependencies. The optional HTTP
backend uses FastAPI, Pydantic and Uvicorn, with a backend Docker Compose service.
PostgreSQL remains for a later stage.

## Installation and tests

From this directory:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[api,test]"
python -m pytest -vv
```

## Architecture

`engine/cards` contains Card, DeckConfig, Deck and uniqueness validation.
`engine/game_state` contains GameState, CapturedCards, PlayerCounts and HistoryEntry.
`engine/combinations` enumerates all sum subsets, `engine/moves` defines immutable
Move objects, and `engine/rules` validates and applies standard Scopa moves.
`engine/scoring` implements category and final scoring; `engine/probabilities`
implements analytical, enumerated and sampled hidden-card distributions.
`backend/app/api` handles HTTP routing, `schemas` defines transport contracts,
`services` adapts requests to engine calls and a replaceable repository,
`models` contains immutable stored game records, and `core` contains service errors.
`docker` contains the backend Dockerfile; Compose currently runs the backend service.

## Model contracts

The standard configuration explicitly specifies denari, coppe, spade, bastoni;
ranks 1–10 and corresponding capture values 1–10. Alternative configurations may
define their own suits, ranks and values. Scoring settings are explicit in ScoringConfig.
Card IDs are stable `suit:rank` strings; custom Card objects are validated against
the exact configured universe when entering a state. Both IDs and physical
`(suit, rank)` pairs must be unique.

Deck operations return new objects. `deal(n)` returns `(cards, remaining_deck)`
and deals from the beginning. `shuffle(seed)` requires an explicit integer seed,
uses a local PRNG and leaves global random state untouched. Reproducibility is
guaranteed for the same Python runtime and input order; this is not a cryptographic
shuffle or a cross-runtime wire protocol.

GameState is a **player-information snapshot**, not a server's complete deal.
`deck` is the full card universe, not the remaining ordered draw pile. Opponent
hidden identities and draw order are deliberately absent. `unknown_cards` is a
candidate pool computed by excluding the union of all known cards; it is not a
probability distribution. `opponent_hand_size` includes known cards;
`draw_pile_size` counts remaining cards. Their hidden counts cannot exceed the
unknown pool. The model accepts partial observations: unused cards may remain
unclassified, and full-deal conservation will be enforced by future rules.

Current zones (table, hands, captures) are disjoint. `played_cards` is a historical
ledger and may overlap table and captures, but cannot overlap hands. Initial table
cards need not be in that ledger. History entries must have strictly increasing
turn numbers, refer to cards in the universe and to played cards in the ledger.
History may be partial; imported history is checked structurally, not replayed.
`evolve(**changes)` revalidates a replacement without mutating the original;
move legality is certified by RulesEngine.apply_move. Scores and scopa counters are nonnegative
integers for both players. Round numbering starts at 1, turn numbering at 0.

## Example state

```python
from engine.cards import Deck
from engine.game_state import GameState

deck = Deck.create()
state = GameState(
    deck=deck,
    player_hand=deck.cards[:3],
    table_cards=deck.cards[3:7],
    opponent_hand_size=3,
    draw_pile_size=30,
)
assert len(state.unknown_cards) == 33
assert state.hidden_opponent_count == 3
next_snapshot = state.evolve(turn_number=1)
assert state.turn_number == 0
```

API and analysis examples will be added when those stages are implemented.

## Rules and manual positions

Standard rules: a matching single card takes priority over all sums. Multiple
matching single cards are separate choices. Otherwise all identity-distinct
subsets summing to the played value are capture choices. A capture is mandatory
for the chosen card when possible; otherwise it is placed on the table. A capture
moves both the played card and captured table cards to the actor's pile.
Clearing the table counts as Scopa except on the final play of the entire round
(both hands empty after the move and draw_pile_size zero). A batch's last play
with cards still available to deal can count as Scopa.

`RulesConfig` explicitly sets single priority, mandatory capture, final-play
Scopa exclusion and the Scopa point value. Defaults implement standard Scopa.
Rules source: https://www.pagat.com/fishing/scopa.html

```python
from engine.rules import RulesEngine

rules = RulesEngine()
moves = rules.get_legal_moves(state)
for move in moves:
    print(move.played_card.id, move.captured_cards, move.creates_scopa)
    assert rules.apply_move(state, move) == move.resulting_state
```

`get_captures(card, table)` returns only captures, not discards; `can_capture`
tests whether any exists. `get_legal_moves(state)` generates each separate action
with capture_type, creates_scopa, immediate_score and resulting_state.
`apply_move` recomputes legality and ignores supplied derived metadata.
`evaluate_move(state, proposed_move)` returns a validated Move with recomputed
metadata and resulting_state; get_legal_moves uses this same evaluation path.
Each evaluated Move exposes is_capture, is_discard, creates_scopa and
resulting_table_cards. For an unevaluated proposal, resulting_table_cards is None;
an empty tuple means an evaluated empty table. Empty resulting tables caused by
final leftover settlement do not imply capture or Scopa. is_scopa also checks
actor, card availability and capture legality, returning False for invalid actions.
IllegalMove is raised for wrong actors, unavailable cards, invalid captures or
discarding instead of mandatory capture. Move's own duplicate-card validation
raises ValueError before rule evaluation.

`last_capture_player` records the owner of the last real capture. Final leftovers
are assigned to that player without an additional Scopa; a final actual capture
updates that owner first. Leftovers are recorded in captured_cards, not in the
history entry's selected capture subset. If a partial imported state lacks the
owner required for final leftovers, IncompleteInformation is raised.

Player-hand generation is exhaustive. Opponent-hand generation requires all
opponent cards to be known; otherwise IncompleteInformation is raised. A revealed
observed opponent action can be applied with an unknown candidate card when a
hidden opponent slot exists. This validates consistency with the observation,
not the hidden card's actual ownership. No cards are sampled or invented.

Empty hands with a nonempty draw pile wait for an externally supplied validated
deal; apply_move does not shuffle, draw hidden cards or start a new round.
Round completion applies to the represented snapshot; the first-stage contract
still permits partial observations rather than requiring all 40 cards accounted
for. Stored player_score/opponent_score remain accumulated prior-round scores;
current-round Scopa is counted separately and exposed in Move.immediate_score.
End-of-round card/denari/sette bello/primiera scoring is handled by ScoringEngine.

Run the seven hand-checkable positions with assertions:

```sh
python -m examples.rules_positions
```

## Scoring

`engine/scoring` separates captured_cards.py, scopa.py, denari.py,
sette_bello.py, primiera.py and final.py. Each has its own unit-test module in
`backend/tests/scoring`. It imports no probability or decision engine modules.

Standard configured points:

| Category | Award |
| --- | --- |
| Captured cards | 1 point to the side with more cards |
| Scopa | 1 point per recorded Scopa, independently for each side |
| Denari | 1 point to the side with more denari |
| Sette Bello | 1 point to the owner of denari rank 7 |
| Primiera | 1 point for the higher eligible Primiera |

Ties for cards, denari and Primiera award no points. Primiera uses the best
captured card of each configured suit according to rank values:
7=21, 6=18, 1=16, 5=15, 4=14, 3=13, 2=12, 8/9/10=10.
Missing any suit makes that side ineligible. A complete Primiera beats an
incomplete one even if its numeric sum is lower. Both incomplete means no point.
PrimieraValue includes best_cards, missing_suits, eligible and the numeric sum
of available best cards; an incomplete numeric sum must not be treated as eligible.

ScoringConfig stores deck configuration, denari suit, Sette Bello rank, Primiera
rank values and all category weights. Custom decks require an explicitly matching
scoring configuration; missing Primiera rank values are rejected. Scopa counts
record events, not weighted points. If changing the Scopa weight, use the same
scopa_points in RulesConfig (move-level immediate score) and ScoringConfig
(round scoring). Never add move-level immediate scores to the round total again.

```python
from engine.cards import Deck
from engine.game_state import GameState, CapturedCards, PlayerCounts
from engine.scoring import ScoringEngine

deck = Deck.create()
state = GameState(
    captured_cards=CapturedCards(
        tuple(c for c in deck.cards if c.rank <= 7),
        tuple(c for c in deck.cards if c.rank > 7),
    ),
    scopa_count=PlayerCounts(2, 1),
    player_score=4,
    opponent_score=8,
)
engine = ScoringEngine()
result = engine.calculate_score(state)
assert result.round_points == PlayerCounts(6, 1)
assert result.total_scores == PlayerCounts(10, 9)
assert result.breakdown.primiera.player.value == 84
assert result.breakdown.primiera.opponent.value == 40
assert state.player_score == 4  # Calculation never mutates the snapshot.
```

`calculate_score` requires empty hands, draw pile and table, plus every configured
card assigned to exactly one capture pile. Partial rounds raise IncompleteRound.
It returns a category breakdown, round points, previous scores and cumulative
total scores without updating GameState. Repeated calculation is pure and safe.
It trusts the structurally validated Scopa counters; complete history replay and
verification that the round was reached by legal play are separate responsibilities.

`evaluate_captures(captures, scopa_counts)` works with partial observations and
returns current standings only. Its round_points property is the sum of categories
on the supplied piles, not a forecast or final score for an unfinished round.
FinalScore covers round and cumulative scoring, not match-win adjudication.

## Fixed scoring regression positions

`examples/scoring_positions.py` defines seven complete snapshots and explicit
hand-calculated ExpectedScore constants. Pytest compares every category's raw
values and points, Primiera eligibility/missing suits, round points and cumulative
totals against these independent constants. These are scoring fixtures, not
claims of complete legally replayed match histories.

```sh
python -m examples.scoring_positions --output scoring-positions-report.md
python -m pytest -v backend/tests/scoring/test_fixed_positions.py
```

The report includes Expected and Actual for every position. Fixtures cover
both players winning, majority ties, missing suits, a complete lower-valued
Primiera winning over an incomplete higher sum, and a Primiera tie.

## Probability engine

The explicit prior is uniform over unknown card assignments consistent with
known card identities and hidden region sizes. It assumes a fair unseen deal;
it does not infer an opponent's strategy from earlier actions. History is used
as a known-card ledger, not as a behavioral likelihood. Arbitrary evidence can
be supplied to a distribution's condition(event) method.

Modules: models.py, config.py, combinatorics.py, exact.py, monte_carlo.py, engine.py.
There is no dependency on Decision Engine or move selection.

ProbabilityState.from_game_state unions and deduplicates known table, hand,
opponent-known, played and captured cards, then excludes them from the universe.
All pools use canonical card-id order; the full Deck order conveys no hidden
draw order. Impossible partitions, card identities and region sizes are rejected.

Let N be the unknown pool size, h the hidden opponent-hand count, d the draw
pile size and u=N-h-d the unassigned count. A PossibleWorld assigns disjoint
unordered card sets to the full opponent_hand (including known cards), draw_pile
and unassigned. Unassigned cards preserve the first-stage partial-state contract;
they must not be silently treated as cards in the draw pile.

World count is C(N,h)*C(N-h,d). Each prior world has weight 1/world_count.
For an unknown card P(opponent hand)=h/N, P(draw pile)=d/N, P(unassigned)=u/N.
Known opponent cards have hand probability 1; cards known elsewhere have 0.
Joint ownership of r specific unknown cards in a region of size s is
C(N-r,s-r)/C(N,s), so card ownership events are not independent.

If K unknown cards satisfy a predicate and s cards occupy a hidden region,
P(X=k)=C(K,k)*C(N-K,s-k)/C(N,s). matching_count_distribution returns exact
Fraction entries indexed by total matching card count, including known opponent
cards. at_least_one_probability returns 1-P(X=0). These calculations remain exact
even when the full world space is too large to enumerate.

next_draw_probability uses uniform hidden draw order: P(next matches)=K/N,
not K/d and not the probability a card belongs to the draw pile. It rejects
empty draw piles. PossibleWorld intentionally does not represent future deal
order; game-tree chance branches over ordered draws are a future stage.

```python
from engine.probabilities import ProbabilityEngine, ProbabilityConfig, Region

engine = ProbabilityEngine(ProbabilityConfig(
    max_exact_worlds=10_000,
    monte_carlo_samples=10_000,
    seed=0,
))
belief = engine.state(state)
distribution = engine.distribution(belief, method="auto")
assert distribution.total_mass == 1
print(distribution.method, belief.world_count)
print(engine.at_least_one_probability(belief, lambda c: c.rank == 7))
event = lambda world: any(c.rank == 7 for c in world.opponent_hand)
estimate = distribution.estimate(event)
print(estimate.probability, estimate.exact, estimate.standard_error)
```

Exact enumeration materializes the full distribution only below the configured
world-count limit. Explicit method="exact" raises EnumerationLimitExceeded
above it. method="auto" chooses exact or monte_carlo based on that limit.
Explicit method="monte_carlo" samples independent uniform worlds without
replacement within each world, aggregates duplicate samples, and uses empirical
weights count/samples. Samples are independent across iterations, so worlds
may repeat. This estimates probabilities; it never randomly chooses a game move.

Monte Carlo uses a local Random(seed), no global RNG, and reports sample count,
seed and exact=False. Identical input/config/seed on the same Python runtime
produces identical weights and ordering. Its plug-in Bernoulli standard error
sqrt(p_hat*(1-p_hat)/samples) is diagnostic, not a guaranteed error bound or
proof that an unobserved event is impossible. Storage is bounded by sample count,
not total world count. Parallel sampling and rollout depth are future simulation
work; this stage provides the mathematical sampling backend.

distribution.condition(evidence) applies Bayes renormalization to represented
worlds. Zero represented mass raises ValueError; for a sampled distribution this
may mean the sample missed the event, not that it is mathematically impossible.
Conditioned sampled distributions remain approximate and do not claim a standard
error based on the original sample count. Analytical engine methods calculate
the original uniform prior from ProbabilityState; use the conditioned distribution
for posterior event queries instead of reusing unconditioned formulas.

Run the hand-checked examples (six exact worlds, 13 exact probability checks,
and a reproducible Monte Carlo comparison):

```sh
python -m examples.probability_calculations --output probability-report.md
python -m pytest -v backend/tests/probabilities
```

Tests cover hypergeometric normalization and expectation across all populations
up to 7, exact enumeration versus analytic marginals, joint/conditional events,
known-card exclusions, partial observations, empty pools, limits, deterministic
sampling, and a 847,660,528-world space handled without exact materialization.

## Game tree

`engine/game_tree` separates config.py, models.py, beliefs.py, evaluation.py,
search.py and export.py. `engine/opponent_model/base.py` defines the injected
OpponentModel protocol and UniformOpponent. The uniform model assigns equal
Fraction weights to every legal action for each concrete opponent hand; it
never randomly selects an action. It is an explicit behavioral assumption,
not a claim that the opponent plays optimally.

```python
from engine.game_tree import GameTree, SearchConfig, save_tree

tree = GameTree(SearchConfig(max_depth=2, max_nodes=5_000))
result = tree.search(state)
print(result.node_count, result.reached_depth, result.root.value)
for node in result.explored_states:
    print(node.id, node.depth, node.probability, node.evaluation.total, node.value)
save_tree(result, "game-tree.json")
```

SearchResult retains all explored TreeNodes: GameState, posterior belief,
parent/child IDs, move/drawn-card event, depth, branch_probability, cumulative
probability, local evaluation, backed-up value and stop reason. JSON export
stores every observed state and branch metadata, using numerator/denominator
pairs for fractions. It exports belief summaries; full hidden-world lists remain
in SearchResult. The JSON is a review artifact, not a resumable checkpoint.

Player nodes expand all legal moves. Values are backed up as a maximum over
player alternatives and weighted averages over opponent/chance outcomes.
Player moves have branch_probability=None: decisions are not random events.
Their cumulative probability copies the parent's probability, conditional on
that chosen player-action path. Summing masses across player alternatives is
not meaningful. Opponent/chance children have normalized conditional probabilities
and multiply cumulative path mass.

Opponent hands remain hidden in public successor states. For each belief world,
legal actions and policy weights are calculated, then identical observed actions
are grouped. Bayes likelihood weighting produces the successor posterior,
which persists through later moves instead of resetting to the uniform prior.
Player choices are made at shared belief nodes, not separately for hidden hands.
Supplied conditioned beliefs are accepted when matching the root observation.
Exact priors remain exact; sampled priors retain monte_carlo/seed/sample metadata.

Depth counts played cards by both players. Chance/deal steps do not consume
move depth. When both hands empty, the next batch is dealt even at a move-depth
cutoff, so the leaf records the next playable state. max_depth=0 with nonempty
hands gives one cutoff; an empty-hand root with a draw pile expands the deal first.

Unknown-card nodes reveal player draws one at a time, without replacement.
Opponent allocation is marginalized over hidden hands at the last player draw.
Uniform hidden order makes this grouping equivalent to unordered batch allocation;
no actions occur during a batch. cards_per_hand defaults to 3 and first_player
defaults to player. Even short piles deal min(cards_per_hand,pile_size/2) per
side; odd piles are rejected. Dealing reduces draw_pile_size but changes neither
turn_number nor round_number: a batch belongs to the same scoring round.
Intermediate deal states are marked CHANCE, not playable turns.

PositionEvaluator has configurable nonnegative Fraction weights. At complete
terminal rounds, default weights give the real cumulative score difference.
At cutoffs/partial rounds it uses a heuristic: captured-card count difference
divided by deck size, denari difference divided by suit size, available Primiera
strength difference divided by maximum strength, plus actual Scopa/Sette Bello
points and previous score difference. Raw strengths do not imply eligibility
or predict final category awards. Nodes store source=heuristic or terminal_score
and category contributions. Root value is a depth-limited expected heuristic/score
under the opponent model, not a proven full-game optimal result.

max_nodes and max_belief_worlds bound expansion; exceeding either raises
SearchLimitExceeded without returning a silently truncated tree. Empty acting
hands with nonempty opposing hands are rejected when expanded. Missing final
capture ownership propagates the Rules Engine error. Partial settled states
remain partial_round_complete/heuristic, not falsely scored as complete rounds.
DecisionEngine.analyze integrates this search; no database is added.

```sh
python -m examples.game_tree_positions --output game-tree-example.json
python -m pytest -v backend/tests/game_tree
```

## Decision Engine

`engine/decision_engine` separates config.py, models.py, engine.py and export.py.
Input is GameState on Player.PLAYER's turn. All legal actions are generated and
verified against every root branch of one shared GameTree search; no action is
filtered by number of captured cards. Exhausting search limits raises an error
instead of selecting from an incomplete subset.

```python
from engine.decision_engine import DecisionConfig, DecisionEngine, save_analysis
from engine.game_tree import SearchConfig

engine = DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=2)))
analysis = engine.analyze(state)
print(analysis.recommended_move, analysis.expected_value)
for item in analysis.all_moves:
    print(item.move, item.evaluation.total, item.expected_value,
          item.scopa_probability, item.primiera_value, item.sette_bello_value,
          item.opponent_expected_value)
save_analysis(analysis, "analysis.json")
```

AnalysisResult contains all_moves (MoveAnalysis objects), legal_moves (raw Move
objects), recommended_move, recommended_analysis, the explored tree, root belief,
requested/reached depth, status and calculation_time in seconds. Top-level metric
properties reference the recommended move. Each MoveAnalysis stores immediate
evaluation and expected_evaluation category breakdowns, net expected_value,
player_expected_value and opponent_expected_value, plus these horizon metrics:

| Field | Meaning |
| --- | --- |
| scopa_probability | Probability of at least one NEW player Scopa by the searched horizon, including the root action |
| opponent_scopa_probability | Probability of at least one NEW opponent Scopa in those continuations |
| expected_scopa_count | Expected number of new player Scopas, distinct from probability of any Scopa |
| primiera_value | Expected available best-per-suit raw Primiera sum in the player's capture pile |
| opponent_primiera_value | Corresponding opponent raw sum |
| primiera_eligible_probability | Probability the player's capture pile contains every required suit |
| sette_bello_probability | Probability Sette Bello belongs to the player's captured pile by the horizon |
| sette_bello_value | Expected actual Sette Bello category points, before evaluation weight |
| expected_captured_cards | Expected captured player-pile size, including played cards |
| terminal_probability | Probability outcomes are complete, settled rounds with real final scoring |

These are horizon-dependent predictions under the configured prior/opponent
policy, not claims about events beyond the cutoff. Primiera raw sum alone does
not imply eligibility. Holding Sette Bello in an unplayed hand is not ownership
of its captured-pile scoring point. Existing Scopa counters are subtracted from
event counts, so past Scopas do not count as future success probabilities.

At future player nodes the continuation with largest backed-up value is followed;
opponent/chance nodes retain their conditional probabilities. For each fixed
root action, the saved OutcomeEvaluation entries have probabilities summing to
one. Each identifies a leaf node and includes separate player/opponent utilities
and raw metrics. Expected value is E[player utility] - E[opponent utility],
with each utility obtained from PositionEvaluator.evaluate_sides; opponent value
is not just negative net value. Aggregated component differences are checked
against GameTree.value exactly with Fractions. Immediate score is already in
state counters/evaluation and is never added again.

Recommendations maximize expected_value across ALL root actions. Ties are
resolved by ascending played-card ID, then sorted captured-card IDs; future
player choices use the same tie rule. No random selection occurs. Exactness
metadata refers to the belief/event probabilities and finite-horizon aggregation;
cutoff utility remains an explicitly marked heuristic. expected_evaluation.source
distinguishes expected_terminal_score, expected_heuristic and expected_mixed.
Default opponent behavior remains UniformOpponent, not an optimal adversary.

DecisionConfig bundles SearchConfig (depth must be >=1), ProbabilityConfig and
EvaluationConfig. Rules, scoring and opponent model can be injected; custom
decks require matching scoring configuration. No legal moves returns an empty
all_moves, recommended_move=None, metric properties=None, and round_finished
or no_legal_moves status. Opponent-turn analysis is rejected explicitly.

Same state/config/seed gives identical mathematical results. Wall-clock
calculation_time is nondeterministic metadata, excluded from AnalysisResult
equality and from default deterministic JSON export. save_analysis(...,
include_timing=True) includes it when desired. JSON retains every move's metrics
and leaf outcome details; full explored observations are accessible via tree.

```sh
python -m examples.decision_positions --output-dir .
python -m pytest -v backend/tests/decision_engine
```

The examples assert that the shorter Sette Bello capture beats a three-card
capture and that looking ahead changes a tied immediate decision to avoid a
1/2 opponent Scopa risk. Comprehensive tests cover all-action coverage, metric
aggregation, future Scopa probability, final exact scoring, custom decks/weights,
deterministic ties, sampling metadata, immutable state, empty actions and limits.
Pytest uses importlib mode so same-named test modules in separate component
directories remain independently importable.

## Stage 7: Monte Carlo Simulation Engine

`engine.simulation` samples complete hidden worlds without replacement, uniform
opponent legal actions and ordered future deals. Player actions use a deterministic
greedy policy based on the public observation; `first_legal` is also configurable.
A supplied legal `move` fixes the first player action for evaluating that candidate.
At the depth cutoff the existing position evaluator supplies heuristic utility;
completed rounds use actual scoring. This estimates the configured rollout policy,
not the optimal Decision Engine search strategy.

```python
from engine.simulation import SimulationConfig, SimulationEngine

engine = SimulationEngine(SimulationConfig(
    iterations=5000, seed=123, max_depth=6, workers=2,
    chunk_size=128, confidence=0.95, trace_limit=5,
))
# Call under an if __name__ == "__main__": guard when using process workers.
result = engine.simulate(state)
print(result.expected_value.mean, result.expected_value.standard_error)
print(result.scopa_probability.probability)
comparison = engine.compare_exact(small_state)
```

Each iteration has an independently derived SHA-256 seed. Same input, seed,
policy and depth reproduce all mathematical results in the same Python runtime,
independent of process count, scheduling and chunk size. Aggregation uses exact
Fraction sums and squared sums; time and worker metadata are excluded from default
JSON and equality. Execution uses real spawn-based ProcessPoolExecutor workers.

Mean estimates include unbiased sample variance, standard error, an approximate
normal confidence interval and a conservative Hoeffding interval using bounded
utility ranges. With one sample, variance/standard error/normal interval are
undefined and returned as None. Event probabilities include Wilson score intervals,
including nondegenerate intervals when every sampled outcome is identical.
Confidence is per metric; simultaneous coverage of all metrics is not guaranteed.

`exact_reference` enumerates the same uniform belief and opponent policy, selects
the same public-information player policy, and marginalizes chance branches.
It uses configurable exact-world/node limits; oversized references raise rather
than silently switching methods. `compare_exact` returns all exact values, estimates,
absolute errors and interval coverage. Rollout traces retain observable states,
legal moves and deals without exposing the remaining hidden opponent hand.

```sh
python -m examples.simulation_comparison
python -m pytest -v backend/tests/simulation
python -m pytest -v
```

The report checks manually known probabilities 1/2 and 1/4 and verifies identical
serial/parallel estimates. No API is added at this stage.

### Ten-state convergence benchmark

`python -m examples.simulation_convergence --workers 4` executes exact references
and 1000, 10000, 100000 actual rollouts for each of ten distinct fixed GameStates.
Output is saved in `convergence/`: complete card-zone manifests, all 30 simulation
results, an EV/error table, mean absolute error and root mean squared error.
Seed 123 is fixed; budgets use identical sample prefixes. `--resume` can retain
fully completed rows whose manifest and exact reference agree with the fixtures.
Reported error is absolute EV error, not a probability percentage. The cutoff
evaluation and player/opponent policies match between exact and Monte Carlo.
An individual realized error need not decrease at every larger sample budget.
Batch-local bounded caches reuse immutable rule transitions and evaluations;
every iteration still performs its own seeded hidden-world and action sampling.
Tests compare cached batches with uncached rollout traces and exact sums.

## FastAPI

Run from the project root, using one Uvicorn application worker for the current
in-memory repository (simulation subprocess workers are separate):

```sh
python -m pip install -e ".[api,test]"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Swagger UI: `http://127.0.0.1:8000/docs`; OpenAPI: `/openapi.json`.
`backend/app/main.py` exposes `create_app(repository=...)` for dependency injection
and test isolation. API integration tests use FastAPI TestClient, as described in
the [official testing guide](https://fastapi.tiangolo.com/tutorial/testing/).
The current Starlette client also needs httpx2, included in the test extra.

| Method | URL | Request | Response |
| --- | --- | --- | --- |
| POST | `/api/games` | `{ "state": GameState }` or `{}` | 201: ID, revision, validated state |
| POST | `/api/games/{id}/state` | `{ "state": GameState, "expected_revision": 1 }` | 200: replacement state and incremented revision |
| POST | `/api/games/{id}/analyze` | analysis options, or `{}` | 200: all legal moves, evaluations, probabilities, recommendation |
| POST | `/api/games/{id}/simulate` | simulation options, or `{}` | 200: means, errors, intervals, event probabilities, optional traces |
| GET | `/api/games/{id}` | none | 200: current game snapshot |
| GET | `/api/games/{id}/analysis` | none | 200: most recent saved analysis of the current revision |

Requests have typed Pydantic schemas; unknown fields are rejected. HTTP handlers
only call GameService. The service invokes GameState, DecisionEngine and
SimulationEngine. All capture, scoring, evaluation and probability logic remains
inside engine. Card IDs in state zones refer to the supplied deck; the default
deck is standard 40-card Scopa. Supply full card objects in `state.deck` for custom
universes; calculation services currently use standard rules/scoring defaults
and engine rejects incompatible decks rather than guessing scoring parameters.

State upload replaces the complete observation; omitted fields use defaults.
It does not represent applying a legal move or automatically deal cards. Revision
starts at 1. An optional expected_revision protects uploads from concurrent
changes. Every update invalidates saved analysis and simulation. Calculations
use immutable snapshots; saving a result checks that its source revision is still
current, otherwise returns 409 instead of publishing an obsolete calculation.

Exact fractions are JSON objects `{ "numerator": 1, "denominator": 2 }`, including
EV and event probabilities. Per-move resulting states and horizon outcomes are
retained. Analysis probability metadata includes method, world count and sampling
seed/count. Simulation means include standard error, approximate confidence
interval and Hoeffding interval; event intervals use Wilson. Elapsed calculation
time is runtime metadata and may change on repeated requests.

Analysis options: max_depth, max_nodes, max_belief_worlds, max_exact_worlds,
probability_method, monte_carlo_samples, seed, cards_per_hand, first_player.
Simulation options: iterations, seed, max_depth, workers, chunk_size, confidence,
trace_limit, cards_per_hand, first_player, player_policy and optional initial move
`{ "played_card": "coppe:4", "captured_cards": [] }`. Resource caps are visible
in OpenAPI. POST analyze/simulate are synchronous and complete the calculation
before returning; engine calls run in synchronous endpoint worker threads.

404 means game or current analysis is absent; 422 means invalid JSON/state/move
or incompatible engine input; 409 means revision conflict; 429 means configured
exact enumeration/search limits were exceeded. Failed calculations do not save
partial results or mutate the uploaded state.

Storage is an actual thread-safe in-memory repository scoped to one application
process. Data is lost on restart and is not shared between Uvicorn workers.
PostgreSQL persistence and authentication are not part of this stage.

Example creating a position, then analyzing and simulating it:

```json
{
  "state": {
    "player_hand": ["coppe:8"],
    "table_cards": ["denari:1", "denari:2", "denari:3", "denari:5", "denari:7"],
    "opponent_hand_size": 1
  }
}
```

Use the returned id for POST analyze with `{ "max_depth": 1 }`. All three
legal captures are returned: 1+7, 3+5, 1+2+5. POST simulate with
`{ "iterations": 1000, "seed": 123, "max_depth": 2 }` returns reproducible
mathematical estimates. `python -m examples.api_demo` exercises all six routes
against the running HTTP server and writes its request/response transcript.

```sh
python -m pytest -v backend/tests/api
python -m pytest -v
```
