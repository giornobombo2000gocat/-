from fractions import Fraction as F
from math import comb
import pytest

from engine.cards import Card, Deck
from engine.game_state import GameState
from engine.probabilities import ProbabilityEngine, ProbabilityState, Region, hypergeometric_pmf

ENGINE = ProbabilityEngine()


def test_manual_hypergeometric_two_sevens_in_four_cards():
    assert hypergeometric_pmf(4,2,2) == (F(1,6), F(2,3), F(1,6))


@pytest.mark.parametrize("args", [(0,0,0), (4,0,2), (4,4,2), (4,2,0), (4,2,4)])
def test_hypergeometric_boundary_normalization(args):
    assert sum(hypergeometric_pmf(*args)) == 1


@pytest.mark.parametrize("args", [(-1,0,0), (4,5,2), (4,2,5), (4,True,1)])
def test_hypergeometric_invalid_inputs(args):
    with pytest.raises(ValueError):
        hypergeometric_pmf(*args)


def test_all_small_hypergeometric_spaces_normalize():
    for n in range(8):
        for k in range(n+1):
            for h in range(n+1):
                pmf = hypergeometric_pmf(n,k,h)
                assert sum(pmf) == 1
                assert sum((i*p for i,p in enumerate(pmf)),F()) == (F(h*k,n) if n else 0)


def test_specific_card_probability_and_draw(small_state,pool):
    assert ENGINE.card_probability(small_state,pool[0]) == F(1,2)
    assert ENGINE.card_probability(small_state,pool[0],Region.DRAW_PILE) == F(1,2)
    assert ENGINE.card_probability(small_state,pool[0],Region.UNASSIGNED) == 0


def test_cards_in_hand_are_dependent_not_independent(small_state,pool):
    assert ENGINE.all_cards_probability(small_state,pool[:2]) == F(1,6)
    assert ENGINE.all_cards_probability(small_state,pool[:2]) != F(1,2)**2
    assert ENGINE.all_cards_probability(small_state,pool[:3]) == 0
    assert ENGINE.all_cards_probability(small_state,()) == 1


def test_unknown_sevens_count_and_at_least_one(small_state):
    match = lambda c: c.rank == 7
    assert ENGINE.matching_count_distribution(small_state,match) == (F(1,6),F(2,3),F(1,6))
    assert ENGINE.at_least_one_probability(small_state,match) == F(5,6)


def test_next_draw_is_not_probability_of_pile_membership(small_state,pool):
    state = small_state.evolve(opponent_hand_size=1,draw_pile_size=3)
    assert ENGINE.card_probability(state,pool[0],Region.DRAW_PILE) == F(3,4)
    assert ENGINE.next_draw_probability(state,lambda c:c == pool[0]) == F(1,4)
    assert ENGINE.next_draw_probability(state,lambda c:c.rank == 7) == F(1,2)


def test_known_opponent_card_offsets_matching_count(small_state,pool):
    state = small_state.evolve(opponent_known_cards=(pool[0],))
    assert ENGINE.card_probability(state,pool[0]) == 1
    assert ENGINE.card_probability(state,pool[0],Region.DRAW_PILE) == 0
    assert ENGINE.matching_count_distribution(state,lambda c:c.rank==7) == (F(0),F(2,3),F(1,3))
    assert ENGINE.at_least_one_probability(state,lambda c:c.rank==7) == 1
    assert ENGINE.all_cards_probability(state,pool[:2]) == F(1,3)


def test_known_nonmatch_preserves_full_hand_support(small_state,pool):
    state = small_state.evolve(opponent_known_cards=(pool[2],))
    assert ENGINE.matching_count_distribution(state,lambda c:c.rank==7) == (F(1,3),F(2,3),F(0))


def test_known_elsewhere_has_zero_hand_probability(small_state):
    card = small_state.captured_cards.opponent[0]
    assert ENGINE.card_probability(small_state,card) == 0
    assert ENGINE.all_cards_probability(small_state,(card,)) == 0


def test_empty_unknown_pool_no_division_by_zero():
    deck = Deck.create()
    state = GameState(player_hand=deck.cards)
    assert ENGINE.card_probability(state,deck.cards[0]) == 0
    assert ENGINE.matching_count_distribution(state,lambda c:True) == (F(1),)
    assert ENGINE.all_cards_probability(state,()) == 1


def test_empty_draw_has_no_next_card(small_state):
    with pytest.raises(ValueError):
        ENGINE.next_draw_probability(small_state.evolve(draw_pile_size=0),lambda c:True)


def test_early_scopa_position_hand_calculation():
    deck = Deck.create()
    cards = {c.id:c for c in deck.cards}
    state = GameState(player_hand=tuple(cards[f"coppe:{r}"] for r in (1,2,3)),
                      table_cards=tuple(cards[f"denari:{r}"] for r in (1,2,3,4)),
                      opponent_hand_size=3,draw_pile_size=30)
    p = ProbabilityState.from_game_state(state)
    assert len(p.unknown_cards)==33
    assert p.world_count==comb(33,3)==5456
    assert ENGINE.card_probability(state,cards["denari:7"])==F(1,11)
    assert ENGINE.at_least_one_probability(state,lambda c:c.rank==7)==F(901,2728)
    assert ENGINE.next_draw_probability(state,lambda c:c.rank==7)==F(4,33)


def test_foreign_card_rejected(small_state):
    with pytest.raises(ValueError):
        ENGINE.card_probability(small_state,Card("x","foreign",1,1))


def test_duplicate_query_card_rejected(small_state,pool):
    with pytest.raises(ValueError):
        ENGINE.all_cards_probability(small_state,(pool[0],pool[0]))


def test_unassigned_region_marginal(small_state,pool):
    state = small_state.evolve(opponent_hand_size=1,draw_pile_size=1)
    assert ENGINE.card_probability(state,pool[0],Region.UNASSIGNED)==F(1,2)
    assert ENGINE.matching_count_distribution(state,lambda c:c.rank==7,Region.UNASSIGNED)==(F(1,6),F(2,3),F(1,6))
