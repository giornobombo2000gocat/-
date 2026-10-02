from dataclasses import FrozenInstanceError, replace
import pytest

from engine.cards import Card, Deck
from engine.game_state import CapturedCards, GameState
from engine.probabilities import ProbabilityState, PossibleWorld, ProbabilityConfig


def test_known_unknown_union_deduplicates_played_and_captured(pool):
    deck = Deck.create()
    excluded = tuple(c for c in deck.cards if c not in pool)
    state = GameState(table_cards=(pool[0],), player_hand=(pool[1],),
                      opponent_known_cards=(pool[2],), opponent_hand_size=2,
                      played_cards=(excluded[0],), captured_cards=CapturedCards(excluded,()))
    p = ProbabilityState.from_game_state(state)
    assert len(p.known_cards) == 39
    assert p.unknown_cards == (pool[3],)
    assert p.hidden_opponent_count == 1 and p.world_count == 1


def test_world_count_combination_formula(small_state):
    p = ProbabilityState.from_game_state(small_state)
    assert p.world_count == 6  # C(4,2)*C(2,2)
    assert p.unassigned_count == 0


def test_partial_observation_has_explicit_unassigned(small_state):
    p = ProbabilityState.from_game_state(small_state.evolve(opponent_hand_size=1,draw_pile_size=1))
    assert p.unassigned_count == 2 and p.world_count == 12


def test_input_order_does_not_change_belief(small_state):
    a = ProbabilityState.from_game_state(small_state)
    b = ProbabilityState.from_game_state(small_state.evolve(deck=Deck(tuple(reversed(small_state.deck.cards)))))
    assert a == b


def test_belief_is_immutable(small_state):
    p = ProbabilityState.from_game_state(small_state)
    with pytest.raises(FrozenInstanceError):
        p.draw_pile_size = 0


def test_bad_partition_rejected(small_state):
    p = ProbabilityState.from_game_state(small_state)
    with pytest.raises(ValueError):
        replace(p, unknown_cards=p.unknown_cards[:-1])


def test_too_many_hidden_cards_rejected(small_state):
    with pytest.raises(ValueError):
        replace(ProbabilityState.from_game_state(small_state), hidden_opponent_count=5)


def test_known_opponent_must_be_known(small_state, pool):
    with pytest.raises(ValueError):
        replace(ProbabilityState.from_game_state(small_state),opponent_known_cards=(pool[0],))


def test_world_regions_must_be_disjoint(pool):
    with pytest.raises(ValueError):
        PossibleWorld((pool[0],),(pool[0],))


@pytest.mark.parametrize("changes", [{"max_exact_worlds":0}, {"monte_carlo_samples":-1}, {"seed":None}, {"seed":True}])
def test_invalid_config(changes):
    with pytest.raises(ValueError):
        ProbabilityConfig(**changes)
