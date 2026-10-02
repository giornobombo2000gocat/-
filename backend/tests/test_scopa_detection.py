from dataclasses import replace

import pytest

from engine.cards import Deck
from engine.game_state import GameState, Player, PlayerCounts
from engine.moves import CaptureType, Move
from engine.rules import IllegalMove, RulesEngine

CARDS = {c.id: c for c in Deck.create().cards}
RULES = RulesEngine()


def position(value, table, *, final=False):
    return GameState(player_hand=(CARDS[f"coppe:{value}"],),
                     table_cards=tuple(CARDS[f"denari:{v}"] for v in table),
                     opponent_hand_size=0 if final else 1)


def test_ordinary_capture_detection_and_resulting_table():
    state = position(5, (2, 3, 9))
    move = RULES.evaluate_move(state, Move(state.player_hand[0], state.table_cards[:2]))
    assert move.is_capture and not move.is_discard
    assert move.capture_type == CaptureType.SUM
    assert not move.creates_scopa and move.immediate_score == 0
    assert move.resulting_table_cards == (CARDS["denari:9"],)
    assert move.resulting_state.scopa_count == PlayerCounts()


@pytest.mark.parametrize("value,table,capture_type", [(5, (2, 3), CaptureType.SUM), (5, (5,), CaptureType.SINGLE)])
def test_capture_all_table_detects_scopa(value, table, capture_type):
    state = position(value, table)
    move = RULES.evaluate_move(state, Move(state.player_hand[0], state.table_cards))
    assert move.is_capture and not move.is_discard
    assert move.capture_type == capture_type
    assert move.creates_scopa and move.immediate_score == 1
    assert move.resulting_table_cards == ()
    assert move.resulting_state.scopa_count.player == 1


def test_non_capture_detection_and_resulting_table():
    state = position(4, (2, 3))
    move = RULES.evaluate_move(state, Move(state.player_hand[0]))
    assert move.is_discard and not move.is_capture
    assert move.capture_type == CaptureType.NONE
    assert not move.creates_scopa
    assert move.resulting_table_cards == state.table_cards + state.player_hand


def test_empty_table_discard_is_not_scopa():
    state = position(8, ())
    move = RULES.get_legal_moves(state)[0]
    assert move.is_discard and not move.creates_scopa
    assert move.resulting_table_cards == state.player_hand


def test_impossible_wrong_sum_scopa_rejected():
    state = position(4, (2, 3))
    proposal = Move(state.player_hand[0], state.table_cards, creates_scopa=True)
    assert not RULES.is_scopa(state, proposal)
    with pytest.raises(IllegalMove):
        RULES.evaluate_move(state, proposal)


def test_impossible_wrong_actor_scopa_rejected():
    state = position(5, (2, 3))
    proposal = Move(state.player_hand[0], state.table_cards, actor=Player.OPPONENT)
    assert not RULES.is_scopa(state, proposal)
    with pytest.raises(IllegalMove):
        RULES.evaluate_move(state, proposal)


def test_impossible_unowned_card_scopa_rejected():
    state = position(9, (2, 3))
    proposal = Move(CARDS["coppe:5"], state.table_cards)
    assert not RULES.is_scopa(state, proposal)
    with pytest.raises(IllegalMove):
        RULES.evaluate_move(state, proposal)


def test_final_capture_empty_table_without_scopa():
    state = position(5, (2, 3), final=True)
    move = RULES.get_legal_moves(state)[0]
    assert move.is_capture and move.resulting_table_cards == ()
    assert not move.creates_scopa and move.immediate_score == 0


def test_final_discard_empty_table_without_capture_or_scopa():
    state = position(4, (2, 3), final=True).evolve(last_capture_player=Player.OPPONENT)
    move = RULES.get_legal_moves(state)[0]
    assert move.is_discard and not move.is_capture
    assert move.resulting_table_cards == ()
    assert not move.creates_scopa


def test_multiple_capture_options_have_separate_detection_results():
    state = position(8, (1, 2, 3, 5, 7))
    expected = {(1, 2, 5): (3, 7), (1, 7): (2, 3, 5), (3, 5): (1, 2, 7)}
    moves = RULES.get_legal_moves(state)
    assert len(moves) == 3
    for move in moves:
        capture = tuple(sorted(c.value for c in move.captured_cards))
        assert move.is_capture and not move.is_discard and not move.creates_scopa
        assert tuple(sorted(c.value for c in move.resulting_table_cards)) == expected[capture]


def test_two_single_captures_do_not_clear_table():
    state = position(5, (5,)).evolve(table_cards=(CARDS["denari:5"], CARDS["spade:5"]))
    moves = RULES.get_legal_moves(state)
    assert len(moves) == 2
    assert all(m.is_capture and not m.creates_scopa and len(m.resulting_table_cards) == 1 for m in moves)


def test_evaluation_recomputes_forged_detection_metadata():
    state = position(4, (2, 3))
    proposal = Move(state.player_hand[0], creates_scopa=True, capture_type=CaptureType.SUM,
                    immediate_score=999, resulting_state=state.evolve(table_cards=()))
    evaluated = RULES.evaluate_move(state, proposal)
    assert evaluated.is_discard and evaluated.capture_type == CaptureType.NONE
    assert not evaluated.creates_scopa and evaluated.immediate_score == 0
    assert evaluated.resulting_table_cards == state.table_cards + state.player_hand
    assert proposal.creates_scopa  # Evaluation does not mutate the caller's object.


def test_unevaluated_table_is_distinct_from_empty_result():
    state = position(5, (2, 3))
    proposal = Move(state.player_hand[0], state.table_cards)
    assert proposal.resulting_table_cards is None
    evaluated = RULES.evaluate_move(state, proposal)
    assert evaluated.resulting_table_cards == ()


def test_evaluated_move_is_idempotent_and_matches_transition():
    state = position(5, (2, 3)).evolve(scopa_count=PlayerCounts(2, 1))
    move = RULES.get_legal_moves(state)[0]
    assert RULES.evaluate_move(state, move) == move
    assert RULES.apply_move(state, move) == move.resulting_state
    assert move.resulting_state.scopa_count == PlayerCounts(3, 1)
    assert state.scopa_count == PlayerCounts(2, 1)
