from engine.simulation.full_game import play_round, play_batch


def test_complete_round_conserves_all_cards():
    result = play_round(0, 17)
    assert result.turns == 36
    assert result.captured_cards == 40
    assert result.player_points >= result.player_scopa
    assert result.opponent_points >= result.opponent_scopa


def test_round_reproducible():
    assert play_round(1, 19) == play_round(1, 19)


def test_starters_balanced_and_batch_independent():
    results = play_batch((0, 1), 23)
    assert [r.starter for r in results] == ["player", "opponent"]
    assert results == (play_round(0, 23), play_round(1, 23))


def test_round_outcomes_follow_final_scores():
    for result in play_batch(tuple(range(4)), 29):
        expected = "win" if result.player_points > result.opponent_points else "loss" if result.player_points < result.opponent_points else "draw"
        assert result.outcome == expected


def test_fast_policy_matches_decision_engine_except_invariant_deals():
    assert play_round(0, 31, verify_decisions=True) == play_round(0, 31)
    assert play_round(1, 31, verify_decisions=True) == play_round(1, 31)


def test_depth_one_evaluation_is_invariant_under_pending_deal():
    from engine.cards import Deck
    from engine.game_state import GameState
    from engine.game_tree import PositionEvaluator
    cards = Deck.create().cards
    pending = GameState(table_cards=cards[:4], draw_pile_size=36)
    dealt = pending.evolve(player_hand=cards[4:7], opponent_hand_size=3, draw_pile_size=30)
    evaluator = PositionEvaluator()
    assert evaluator.evaluate(pending) == evaluator.evaluate(dealt)
