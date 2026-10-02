# Offline training adapter boundary

This package implements **synthetic offline training observations only**.
It is not a live Betsson.it integration and the fixture format is not a verified
Betsson payload, DOM layout, protocol or ruleset. No website extraction, login,
network calls, polling, credentials, browser control or move submission is provided.
There is no integration supplying recommendations during real-money play.

The name identifies the requested isolation boundary and mock test harness.
`format_version`, `mode` and `variant` explicitly identify local fixture semantics;
these declarations do not verify the origin of any supplied data.

## Architecture

```text
Synthetic in-memory snapshot
  -> MockSnapshot validation
  -> StateParser
  -> ParsedObservation(GameState + source status)
  -> existing DecisionEngine
  -> AdapterResult(all moves and mathematical evaluations)
```

`models.py` defines frozen Pydantic input models and immutable output envelopes.
`state_parser.py` resolves canonical card IDs and delegates state invariants to
GameState, round completion to RulesEngine and finished-round validation to
ScoringEngine. `adapter.py` defines the read-only BetssonAdapter Protocol and its
only concrete implementation, MockBetssonAdapter. All calculations are delegated
to the existing DecisionEngine; no scoring/capture/probability/search code is copied.

Engine files are unchanged and do not import site_adapter, backend or Pydantic.
The adapter does not depend on FastAPI or frontend. Parser lifecycle checks reject
contradictory observations; they do not implement game rules or select actions.

The engine's existing GameState has no `game_status` field. Source status stays
in ParsedObservation instead of changing the shared mathematical model. The
engine still receives its standard validated immutable GameState.

## Fixture contract

See [fixtures/risk-training.json](fixtures/risk-training.json) for a complete
40-card standard-Scopa training observation with two unknown candidates.

Required fields:

- `format_version`: `scopa-training-v1`
- `mode`: `offline_training`
- `variant`: `standard_scopa`
- `snapshot_id`: nonempty local fixture identifier
- `game_status`: `active`, `waiting_deal` or `finished`
- `player_hand`, `table_cards`, `known_played_cards`: canonical card IDs
- `captured_cards`: player/opponent captured card IDs
- `score`: cumulative player/opponent score before the current round
- `scopa_count`: player/opponent Scopa counts in this round
- `current_player`: `player` or `opponent`
- `turn_number`: zero-based completed move count; `round_number`: one-based
- `opponent_hand_size`: total hand size, including any known cards
- `draw_pile_size`: number of undealt cards

Optional: opponent_known_cards, last_capture_player and game_history.
Captured cards and hidden counts are required because position evaluation and
probability calculation cannot safely infer them from the visible table and hand.
Unavailable inputs are rejected instead of being replaced by guessed empty piles
or arbitrary hidden cards. Unassigned unknown cards retain the existing engine
semantics; unknown pool is not treated as the ordered remaining draw pile.

Finished status requires a fully settled round accepted by ScoringEngine.
Waiting-deal status requires empty hands and a nonempty draw pile. An active
snapshot must contain cards for its acting side. Played history is validated by
the existing GameState, including allowed historical overlaps with capture piles.
External card aliases and site-specific displays are not guessed.

## Usage

Install from repository root:

```sh
python -m pip install -e ".[adapters]"
python -m examples.mock_adapter_analysis
python -m pytest -v backend/tests/site_adapter
python -m pytest -v
```

```python
import json
from pathlib import Path
from engine.decision_engine import DecisionConfig, DecisionEngine
from engine.game_tree import SearchConfig
from site_adapter.betsson import MockBetssonAdapter

fixture = json.loads(Path('site_adapter/betsson/fixtures/risk-training.json').read_text())
adapter = MockBetssonAdapter(
    [fixture], engine=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=2)))
)
state = adapter.get_game_state()
result = adapter.analyze()
print(result.recommended_move.played_card.id)  # coppe:6 (synthetic fixture)
print(result.expected_value)                 # 1115/336
for move in result.all_moves:
    print(move.move.played_card.id, move.expected_value)
```

Results expose legal_moves, all_moves (each evaluation and horizon metrics),
recommended_move, expected_value, scopa_probability, primiera_value,
sette_bello_value, opponent_expected_value and calculation_time. Fractions remain
exact. Timing is measured by DecisionEngine and does not participate in engine
result equality. `result.analysis` retains the full existing AnalysisResult,
including probabilities, outcome details and explored tree.

An opponent turn returns `waiting_for_opponent`; pending deals return
`waiting_for_deal`; completed games return `game_finished`. In these cases
analysis/recommendation/EV/time are None and legal/all moves are empty, so no
player decision is invented. Analysis/resource errors propagate for actionable
positions rather than returning partial recommendations.

Repeated analyze calls never apply or execute the recommended move. `next_snapshot`
only advances the explicit in-memory fixture sequence supplied by a test. It does
not poll a site or modify GameState. Exhaustion raises StopIteration. To explore
a recommendation in a local exercise, the caller may use existing RulesEngine
with the synthetic GameState; no operation on an external site is exposed.

## Integration validation

Tests compare parsed state and recommendations with direct engine calls, verify
exact EV fractions, all three captures for 8, Sette Bello preference, correct
state/history mapping, unknown-information boundaries, frozen observations,
explicit replay and lifecycle statuses. Tests reject missing fields, contradictory
zones/statuses and invalid card IDs, check resource limit propagation, forbid
network access and verify engine imports without the adapter/backend/Pydantic.
