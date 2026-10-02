"""Explicit regression position: play 8 against table 1, 2, 3, 5, 7."""
from engine.cards import Deck
from engine.game_state import GameState, PlayerCounts
from engine.moves import CaptureType
from engine.rules import RulesEngine


def test_eight_all_legal_captures_and_resulting_states():
    cards = {c.id: c for c in Deck.create().cards}
    played = cards["coppe:8"]
    table = tuple(cards[f"denari:{value}"] for value in (1, 2, 3, 5, 7))
    # Opponent still holds a card: this is not the final play of the round.
    state = GameState(player_hand=(played,), table_cards=table, opponent_hand_size=1)
    rules = RulesEngine()
    expected = {
        (1, 2, 5): (3, 7),
        (1, 7): (2, 3, 5),
        (3, 5): (1, 2, 7),
    }

    moves = rules.get_legal_moves(state)
    actual = [tuple(sorted(c.value for c in move.captured_cards)) for move in moves]
    assert len(moves) == 3
    assert len(set(actual)) == 3
    assert set(actual) == set(expected)
    assert {frozenset(capture) for capture in rules.get_captures(played, table)} == {
        frozenset(move.captured_cards) for move in moves
    }
    assert all(c.value != played.value for c in table)  # No overriding single 8.

    for move in moves:
        combination = tuple(sorted(c.value for c in move.captured_cards))
        assert sum(combination) == played.value
        assert len(set(move.captured_cards)) == len(move.captured_cards)
        assert move.capture_type == CaptureType.SUM
        assert not move.creates_scopa and move.immediate_score == 0
        after = rules.apply_move(state, move)
        assert after == move.resulting_state
        assert tuple(sorted(c.value for c in after.table_cards)) == expected[combination]
        assert set(after.captured_cards.player) == {played, *move.captured_cards}
        assert len(after.captured_cards.player) == 1 + len(combination)
        assert after.captured_cards.opponent == ()
        assert after.player_hand == ()
        assert after.scopa_count == PlayerCounts()
        assert after.game_history[-1].captured_cards == move.captured_cards
        assert set(after.known_cards) == set(state.known_cards)
        print(
            f"combination={combination}; sum={sum(combination)}; "
            "legal: sum equals 8, distinct table cards, no single 8; "
            f"player captures played 8 + {combination}; "
            f"table_after={expected[combination]}; scopa=False"
        )

    assert state.table_cards == table and state.player_hand == (played,)
