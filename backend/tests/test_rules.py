import pytest

from engine.cards import Deck
from engine.combinations import sum_combinations
from engine.game_state import GameState, Player, CapturedCards, PlayerCounts
from engine.moves import Move, CaptureType
from engine.rules import RulesEngine, RulesConfig, IllegalMove, IncompleteInformation

DECK = Deck.create()
CARDS = {c.id: c for c in DECK.cards}
RULES = RulesEngine()


def card(rank, suit="denari"):
    return CARDS[f"{suit}:{rank}"]


def position(rank, table, **kwargs):
    return GameState(player_hand=(card(rank, "coppe"),),
                     table_cards=tuple(card(r) for r in table), opponent_hand_size=1, **kwargs)


def signatures(captures):
    return {tuple(sorted(c.value for c in capture)) for capture in captures}


def test_all_sum_combinations_known_eight_position():
    table = tuple(card(r) for r in (1, 2, 3, 5, 7))
    assert signatures(RULES.get_captures(card(8, "coppe"), table)) == {(1, 7), (3, 5), (1, 2, 5)}


def test_single_match_overrides_sums():
    s = position(8, (1, 3, 5, 8))
    assert RULES.get_captures(s.player_hand[0], s.table_cards) == ((card(8),),)


def test_multiple_equal_singles_are_separate_choices():
    table = (card(5), card(5, "spade"), card(2), card(3))
    assert set(RULES.get_captures(card(5, "coppe"), table)) == {(card(5),), (card(5, "spade"),)}


def test_equal_values_keep_physical_identity():
    table = (card(2), card(2, "spade"), card(3))
    captures = RULES.get_captures(card(5, "coppe"), table)
    assert len(captures) == 2
    assert {frozenset(c) for c in captures} == {frozenset((card(2), card(3))), frozenset((card(2, "spade"), card(3)))}


def test_no_card_reused_in_sum():
    assert sum_combinations((card(2),), 4) == ()


def test_combination_order_independent():
    table = tuple(card(r) for r in (1, 2, 3, 5, 7))
    assert sum_combinations(table, 8) == sum_combinations(tuple(reversed(table)), 8)


def test_can_capture_true():
    assert RULES.can_capture(card(5, "coppe"), (card(2), card(3)))


def test_can_capture_false():
    assert not RULES.can_capture(card(4, "coppe"), (card(2), card(3)))


def test_empty_table_has_one_discard():
    s = position(4, ())
    moves = RULES.get_legal_moves(s)
    assert len(moves) == 1
    assert moves[0].capture_type == CaptureType.NONE
    assert not moves[0].creates_scopa


def test_each_combination_is_a_move():
    moves = RULES.get_legal_moves(position(8, (1, 2, 3, 5, 7)))
    assert len(moves) == 3
    assert all(m.capture_type == CaptureType.SUM and m.resulting_state is not None for m in moves)


def test_all_cards_in_hand_generate_moves():
    s = position(5, (2, 3)).evolve(player_hand=(card(5, "coppe"), card(4, "coppe")))
    assert {m.played_card for m in RULES.get_legal_moves(s)} == set(s.player_hand)


def test_mandatory_capture_has_no_discard():
    moves = RULES.get_legal_moves(position(5, (2, 3)))
    assert len(moves) == 1 and moves[0].captured_cards


def test_capture_moves_played_card_to_owned_pile():
    s = position(5, (2, 3, 9))
    after = RULES.apply_move(s, Move(s.player_hand[0], (card(2), card(3))))
    assert set(after.captured_cards.player) == {card(5, "coppe"), card(2), card(3)}
    assert after.table_cards == (card(9),)
    assert after.player_hand == ()
    assert after.played_cards == (card(5, "coppe"),)


def test_discard_adds_card_to_table():
    s = position(4, (2, 3))
    after = RULES.apply_move(s, Move(s.player_hand[0]))
    assert after.table_cards == s.table_cards + s.player_hand
    assert after.captured_cards == CapturedCards()


def test_transition_updates_turn_and_history():
    s = position(4, (2, 3)).evolve(turn_number=7, round_number=2)
    after = RULES.apply_move(s, Move(s.player_hand[0]))
    assert after.current_player == Player.OPPONENT
    assert after.turn_number == 8 and after.round_number == 2
    assert after.game_history[-1].turn_number == 8
    assert after.game_history[-1].actor == Player.PLAYER


def test_state_original_unchanged_and_card_conservation():
    s = position(5, (2, 3, 9))
    before = s.known_cards
    after = RULES.get_legal_moves(s)[0].resulting_state
    assert s.player_hand == (card(5, "coppe"),)
    assert set(after.known_cards) == set(before)
    assert after.unknown_cards == s.unknown_cards


def test_scopa_sum_awards_counter_and_move_point():
    s = position(5, (2, 3))
    move = RULES.get_legal_moves(s)[0]
    assert move.creates_scopa and move.immediate_score == 1
    assert move.resulting_state.scopa_count == PlayerCounts(1, 0)
    assert move.resulting_state.table_cards == ()


def test_single_card_scopa():
    assert RULES.get_legal_moves(position(5, (5,)))[0].creates_scopa


def test_partial_capture_is_not_scopa():
    assert not RULES.get_legal_moves(position(5, (2, 3, 9)))[0].creates_scopa


def test_final_play_capture_is_not_scopa():
    s = position(5, (2, 3)).evolve(opponent_hand_size=0)
    move = RULES.get_legal_moves(s)[0]
    assert not move.creates_scopa and move.immediate_score == 0
    assert move.resulting_state.scopa_count == PlayerCounts()
    assert RULES.round_finished(move.resulting_state)


def test_last_card_of_batch_with_draw_pile_can_scopa():
    s = position(5, (2, 3), draw_pile_size=10).evolve(opponent_hand_size=0)
    assert RULES.get_legal_moves(s)[0].creates_scopa


def test_final_partial_capture_collects_leftovers_without_scopa():
    s = position(5, (2, 3, 9)).evolve(opponent_hand_size=0)
    after = RULES.get_legal_moves(s)[0].resulting_state
    assert after.table_cards == ()
    assert len(after.captured_cards.player) == 4
    assert after.scopa_count == PlayerCounts()
    assert after.game_history[-1].captured_cards == (card(2), card(3))


def test_final_discard_awards_table_to_previous_capturer():
    s = position(4, (2, 3)).evolve(opponent_hand_size=0, last_capture_player=Player.OPPONENT)
    after = RULES.get_legal_moves(s)[0].resulting_state
    assert set(after.captured_cards.opponent) == {card(2), card(3), card(4, "coppe")}
    assert after.table_cards == () and after.scopa_count == PlayerCounts()


def test_final_discard_without_capture_owner_rejected():
    s = position(4, (2, 3)).evolve(opponent_hand_size=0)
    with pytest.raises(IncompleteInformation):
        RULES.apply_move(s, Move(s.player_hand[0]))


def test_illegal_card_not_in_hand():
    with pytest.raises(IllegalMove):
        RULES.apply_move(position(5, (2, 3)), Move(card(9, "coppe")))


def test_illegal_wrong_actor():
    s = position(5, (2, 3))
    with pytest.raises(IllegalMove):
        RULES.apply_move(s, Move(s.player_hand[0], actor=Player.OPPONENT))


def test_illegal_discard_when_capture_exists():
    s = position(5, (2, 3))
    with pytest.raises(IllegalMove):
        RULES.apply_move(s, Move(s.player_hand[0]))


def test_illegal_sum_when_single_exists():
    s = position(5, (2, 3, 5))
    with pytest.raises(IllegalMove):
        RULES.apply_move(s, Move(s.player_hand[0], (card(2), card(3))))


def test_illegal_wrong_sum():
    s = position(5, (2, 4))
    with pytest.raises(IllegalMove):
        RULES.apply_move(s, Move(s.player_hand[0], s.table_cards))


def test_illegal_capture_card_not_on_table():
    s = position(5, (2, 3))
    with pytest.raises(IllegalMove):
        RULES.apply_move(s, Move(s.player_hand[0], (card(5),)))


def test_duplicate_capture_rejected():
    with pytest.raises(ValueError):
        Move(card(4, "coppe"), (card(2), card(2)))


def test_reversed_capture_order_is_legal():
    s = position(5, (2, 3))
    assert RULES.apply_move(s, Move(s.player_hand[0], (card(3), card(2)))).table_cards == ()


def test_forged_derived_metadata_ignored():
    s = position(5, (2, 3))
    move = Move(s.player_hand[0], s.table_cards, creates_scopa=False, immediate_score=999, resulting_state=s)
    after = RULES.apply_move(s, move)
    assert after.scopa_count.player == 1
    assert after.player_score == s.player_score


def test_opponent_known_hand_transition():
    s = GameState(player_hand=(card(9, "coppe"),), table_cards=(card(2), card(3)),
                  opponent_known_cards=(card(5, "spade"),), opponent_hand_size=1, current_player=Player.OPPONENT)
    move = RULES.get_legal_moves(s)[0]
    after = move.resulting_state
    assert move.actor == Player.OPPONENT
    assert after.opponent_hand_size == 0 and after.opponent_known_cards == ()
    assert len(after.captured_cards.opponent) == 3 and after.scopa_count.opponent == 1
    assert after.player_hand == s.player_hand and after.current_player == Player.PLAYER


def test_unknown_opponent_hand_cannot_be_enumerated():
    with pytest.raises(IncompleteInformation):
        RULES.get_legal_moves(position(9, (2, 3)).evolve(current_player=Player.OPPONENT))


def test_observed_hidden_opponent_card_can_be_applied():
    s = position(9, (2, 3)).evolve(current_player=Player.OPPONENT)
    after = RULES.apply_move(s, Move(card(5, "spade"), s.table_cards, Player.OPPONENT))
    assert after.opponent_hand_size == 0
    assert card(5, "spade") not in after.unknown_cards
    assert len(after.captured_cards.opponent) == 3


def test_opponent_cannot_play_players_card():
    s = position(9, (2, 3)).evolve(current_player=Player.OPPONENT)
    with pytest.raises(IllegalMove):
        RULES.apply_move(s, Move(s.player_hand[0], actor=Player.OPPONENT))


def test_finished_round_has_no_moves():
    assert RULES.get_legal_moves(GameState()) == ()
    with pytest.raises(IllegalMove):
        RULES.apply_move(GameState(), Move(card(5)))


def test_empty_hand_awaits_external_deal():
    s = GameState(draw_pile_size=6)
    assert RULES.get_legal_moves(s) == ()
    assert not RULES.round_finished(s)


def test_generation_is_deterministic():
    s = position(8, (1, 2, 3, 5, 7))
    assert RULES.get_legal_moves(s) == RULES.get_legal_moves(s)


def test_nonstandard_priority_is_explicit_configuration():
    r = RulesEngine(RulesConfig(single_card_priority=False))
    assert signatures(r.get_captures(card(5, "coppe"), (card(2), card(3), card(5)))) == {(5,), (2, 3)}


def test_scopa_points_configuration():
    move = RulesEngine(RulesConfig(scopa_points=2)).get_legal_moves(position(5, (2, 3)))[0]
    assert move.immediate_score == 2 and move.resulting_state.scopa_count.player == 1


def test_illegal_clear_table_does_not_count_as_scopa():
    s = position(4, (2, 3))
    assert not RULES.is_scopa(s, Move(s.player_hand[0], s.table_cards))


def test_final_capture_replaces_previous_capture_owner():
    s = position(5, (2, 3, 9)).evolve(opponent_hand_size=0, last_capture_player=Player.OPPONENT)
    after = RULES.get_legal_moves(s)[0].resulting_state
    assert after.last_capture_player == Player.PLAYER
    assert len(after.captured_cards.player) == 4 and after.captured_cards.opponent == ()


def test_two_successive_turns_history_and_captures():
    s = GameState(player_hand=(card(5, "coppe"),), opponent_known_cards=(card(9, "spade"),),
                  opponent_hand_size=1, table_cards=(card(2), card(3), card(9)))
    after = RULES.get_legal_moves(s)[0].resulting_state
    terminal = RULES.get_legal_moves(after)[0].resulting_state
    assert terminal.turn_number == 2 and len(terminal.game_history) == 2
    assert len(terminal.captured_cards.player) == 3
    assert len(terminal.captured_cards.opponent) == 2
    assert terminal.scopa_count == PlayerCounts()
