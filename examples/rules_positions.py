"""Run from the project root: python -m examples.rules_positions."""
from engine.cards import Deck
from engine.game_state import GameState, Player
from engine.moves import Move
from engine.rules import IllegalMove, RulesEngine

CARDS = {c.id: c for c in Deck.create().cards}
RULES = RulesEngine()


def position(rank: int, table: tuple[int, ...], final: bool = False, last=None) -> GameState:
    return GameState(player_hand=(CARDS[f"coppe:{rank}"],),
                     table_cards=tuple(CARDS[f"denari:{r}"] for r in table),
                     opponent_hand_size=0 if final else 1, last_capture_player=last)


def check(name, state, expected_captures, expected_scopa, expected_tables):
    moves = RULES.get_legal_moves(state)
    captures = [tuple(sorted(c.value for c in m.captured_cards)) for m in moves]
    assert set(captures) == set(expected_captures)
    assert [m.creates_scopa for m in moves] == expected_scopa
    tables = [tuple(sorted(c.value for c in m.resulting_state.table_cards)) for m in moves]
    assert sorted(tables) == sorted(expected_tables)
    print(f"PASS {name}: captures={captures}; scopa={[m.creates_scopa for m in moves]}; table_after={tables}")


def main():
    check("A: 8 on [1,2,3,5,7]", position(8, (1, 2, 3, 5, 7)),
          [(1, 2, 5), (1, 7), (3, 5)], [False] * 3, [(3, 7), (2, 3, 5), (1, 2, 7)])
    check("B: single priority, 5 on [2,3,5]", position(5, (2, 3, 5)),
          [(5,)], [False], [(2, 3)])
    check("C: scopa, 5 on [2,3]", position(5, (2, 3)), [(2, 3)], [True], [()])
    check("D: discard, 4 on [2,3]", position(4, (2, 3)), [()], [False], [(2, 3, 4)])
    check("E: final capture, no scopa", position(5, (2, 3), final=True),
          [(2, 3)], [False], [()])
    final_discard = position(4, (2, 3), final=True, last=Player.OPPONENT)
    check("F: final discard, leftovers to opponent", final_discard, [()], [False], [()])
    after = RULES.get_legal_moves(final_discard)[0].resulting_state
    assert set(c.value for c in after.captured_cards.opponent) == {2, 3, 4}
    illegal = position(5, (2, 3, 5))
    try:
        RULES.apply_move(illegal, Move(illegal.player_hand[0], illegal.table_cards[:2]))
    except IllegalMove:
        print("PASS G: sum [2,3] rejected because single 5 exists")
    else:
        raise AssertionError("Illegal sum was accepted")
    print("ALL 7 MANUAL POSITIONS PASSED")


if __name__ == "__main__":
    main()
