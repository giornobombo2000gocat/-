from dataclasses import replace
import pytest
from engine.cards import Deck
from engine.rules import IllegalMove
from engine.simulation.multiplayer import MultiplayerState, MultiplayerMove, MultiplayerResult, apply_move, legal_moves, final_points, recommend, play_round


def cards(*ranks):
    return tuple(next(c for c in Deck.create().cards if c.rank == rank and c.suit == "denari") for rank in ranks)


def state(table=(), hands=((),(),(),()), **kwargs):
    return MultiplayerState(table, hands, captures=kwargs.pop("captures", ((),)*4), scopa=kwargs.pop("scopa", (0,)*4), **kwargs)


def test_four_turns_cycle_including_last_seat():
    current = state(cards(10), (cards(1),cards(2),cards(4),cards(8)), draw=cards(9))
    for actor in range(4):
        assert current.turn == actor
        current = apply_move(current, legal_moves(current)[0])
    assert current.turn == 0


def test_capture_combinations():
    current = state(cards(1,2,3,5,7), (cards(8),(),(),()))
    assert {tuple(c.rank for c in m.capture) for m in legal_moves(current)} == {(1,7),(3,5),(1,2,5)}


def test_fourth_seat_scopa():
    current = state(cards(1,2), (cards(4),(),(),cards(3)), turn=3)
    result = apply_move(current, legal_moves(current)[0])
    assert result.scopa == (0,0,0,1) and result.turn == 0 and result.table == ()


def test_last_play_no_scopa():
    current = state(cards(1,2), ((),(),(),cards(3)), turn=3)
    result = apply_move(current, legal_moves(current)[0])
    assert result.scopa == (0,0,0,0)


def test_leftovers_to_fourth_seat():
    current = state(cards(2), (cards(1),(),(),()), last_capture=3)
    result = apply_move(current, legal_moves(current)[0])
    assert set(result.captures[3]) == set(cards(1,2))


def test_four_individual_scoring_not_teams():
    deck = Deck.create().cards
    current = state(captures=tuple(tuple(c for c in deck if c.suit == suit) for suit in ("denari","coppe","spade","bastoni")), scopa=(1,2,3,4))
    assert final_points(current) == (3,2,3,4)


def test_fourth_seat_wins_all_categories():
    current = state(captures=((),(),(),Deck.create().cards), scopa=(0,0,0,2))
    assert final_points(current) == (0,0,0,6)


def test_no_hidden_card_access():
    current = state(cards(1,2), (cards(3,4),cards(5),cards(6),cards(7)))
    other = replace(current, hands=(current.hands[0],cards(8),cards(9),cards(10)))
    assert recommend(current) == recommend(other)


def test_illegal_move_rejected():
    current = state(cards(1,2), (cards(3),cards(4),cards(5),cards(6)))
    with pytest.raises(IllegalMove):
        apply_move(current, MultiplayerMove(cards(3)[0]))


@pytest.mark.parametrize("index", range(4))
def test_complete_four_player_round(index):
    result = play_round(index, 17, players=4)
    assert result == play_round(index, 17, players=4)
    assert len(result.points) == 4 and result.starter == index
    assert result.turns == 36 and result.captured_cards == 40


def test_three_player_results_remain_unchanged():
    from engine.simulation.three_player import play_three_round
    assert play_round(0, 17) == play_three_round(0, 17)


@pytest.mark.parametrize("points,outcome", [((4,3,2,1),"win"),((4,3,2,4),"draw"),((3,1,2,4),"loss")])
def test_four_player_outcome(points,outcome):
    assert MultiplayerResult(0,1,0,points,(0,0,0,0),36,40).outcome == outcome
