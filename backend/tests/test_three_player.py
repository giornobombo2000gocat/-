from dataclasses import replace
import pytest
from engine.cards import Deck
from engine.rules import IllegalMove
from engine.simulation.three_player import ThreeState, ThreeMove, ThreeResult, legal_moves, apply_move, final_points, recommend, play_three_round


def cards(*ranks):
    return tuple(next(c for c in Deck.create().cards if c.rank == rank and c.suit == "denari") for rank in ranks)


def test_combinations():
    state = ThreeState(cards(1,2,3,5,7), (cards(8), cards(9), cards(10)))
    assert {tuple(c.rank for c in m.capture) for m in legal_moves(state)} == {(1,7),(3,5),(1,2,5)}


def test_single_priority_and_mandatory_capture():
    state = ThreeState(cards(3,5,8), ((next(c for c in Deck.create().cards if c.rank==8 and c.suit=="coppe"),), cards(9), cards(10)))
    assert len(legal_moves(state)) == 1
    assert legal_moves(state)[0].capture == cards(8)
    with pytest.raises(IllegalMove):
        apply_move(state, ThreeMove(state.hands[0][0]))


def test_scopa_and_cyclic_turns():
    state = ThreeState(cards(1,2), (cards(3), cards(4), cards(5)))
    result = apply_move(state, legal_moves(state)[0])
    assert result.table == () and result.scopa == (1,0,0) and result.turn == 1
    result = apply_move(result, legal_moves(result)[0])
    assert result.turn == 2 and result.table == cards(4)


def test_final_capture_no_scopa():
    state = ThreeState(cards(1,2), (cards(3), (), ()))
    result = apply_move(state, legal_moves(state)[0])
    assert result.table == () and result.scopa == (0,0,0)


def test_leftovers_go_to_last_capturer():
    state = ThreeState(cards(2), (cards(1), (), ()), last_capture=2)
    result = apply_move(state, legal_moves(state)[0])
    assert set(result.captures[2]) == set(cards(1,2)) and not result.table


def test_duplicate_rejected():
    with pytest.raises(ValueError):
        ThreeState(cards(1), (cards(1), (), ()))


def test_score_all_categories_and_scopa():
    deck = Deck.create().cards
    own = tuple(c for c in deck if c.suit in ("denari","coppe","spade") or c.rank==7)
    rest = tuple(c for c in deck if c not in own)
    state = ThreeState((), ((),(),()), (own,rest[:4],rest[4:]), (2,1,0))
    assert final_points(state) == (6,1,0)


def test_tied_card_category_not_awarded():
    deck = Deck.create().cards
    state = ThreeState((), ((),(),()), (deck[:20],deck[20:],()), (0,0,0))
    # Cards tied, neither has all four suits, only denari + settebello to seat 0.
    assert final_points(state) == (2,0,0)


def test_incomplete_round_rejected():
    with pytest.raises(ValueError):
        final_points(ThreeState((), ((),(),())))


def test_software_does_not_use_private_hand_contents():
    state = ThreeState(cards(1,2), (cards(3,4), cards(5), cards(6)))
    other = replace(state, hands=(state.hands[0], cards(7), cards(8)))
    assert recommend(state) == recommend(other)


@pytest.mark.parametrize("points,outcome", [((3,2,1),"win"),((3,3,1),"draw"),((2,3,2),"loss"),((1,1,1),"draw")])
def test_result_definition(points,outcome):
    assert ThreeResult(0,1,0,points,(0,0,0),36,40).outcome == outcome


@pytest.mark.parametrize("index", [0,1,2])
def test_complete_round_and_reproducibility(index):
    result = play_three_round(index, 17)
    assert result == play_three_round(index, 17)
    assert result.starter == index
    assert result.turns == 36 and result.captured_cards == 40
