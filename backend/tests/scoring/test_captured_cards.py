import pytest
from engine.game_state import CapturedCards, Player, PlayerCounts
from engine.scoring import ScoringConfig, score_captured_cards


@pytest.mark.parametrize("player_size,opponent_size,winner,points", [
    (21, 19, Player.PLAYER, PlayerCounts(1, 0)),
    (19, 21, Player.OPPONENT, PlayerCounts(0, 1)),
    (20, 20, None, PlayerCounts()), (0, 0, None, PlayerCounts()),
])
def test_card_majority_and_ties(deck, player_size, opponent_size, winner, points):
    captures = CapturedCards(deck.cards[:player_size], deck.cards[player_size:player_size + opponent_size])
    result = score_captured_cards(captures)
    assert (result.player_value, result.opponent_value) == (player_size, opponent_size)
    assert result.winner == winner and result.points == points


def test_card_category_awards_one_point_not_card_count(deck):
    assert score_captured_cards(CapturedCards(deck.cards, ())).points == PlayerCounts(1, 0)


def test_card_category_weight(deck):
    assert score_captured_cards(CapturedCards(deck.cards, ()), ScoringConfig(captured_cards_points=3)).points == PlayerCounts(3, 0)
