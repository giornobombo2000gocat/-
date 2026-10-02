import pytest
from engine.game_state import CapturedCards, Player, PlayerCounts
from engine.scoring import ScoringConfig, score_denari


@pytest.mark.parametrize("size,winner,points", [(6, Player.PLAYER, PlayerCounts(1, 0)), (4, Player.OPPONENT, PlayerCounts(0, 1)), (5, None, PlayerCounts())])
def test_denari_majority_and_tie(cards, size, winner, points):
    denari = tuple(cards[f"denari:{r}"] for r in range(1, 11))
    result = score_denari(CapturedCards(denari[:size], denari[size:]))
    assert (result.player_value, result.opponent_value) == (size, 10-size)
    assert result.winner == winner and result.points == points


def test_other_suits_do_not_count_as_denari(cards):
    result = score_denari(CapturedCards((cards["coppe:7"], cards["spade:7"]), (cards["denari:1"],)))
    assert result.points == PlayerCounts(0, 1)
    assert result.player_value == 0


def test_no_denari_is_tie():
    assert score_denari(CapturedCards()).points == PlayerCounts()


def test_denari_suit_and_weight_are_configured(cards):
    result = score_denari(CapturedCards((cards["coppe:1"],), (cards["denari:1"],)), ScoringConfig(denari_suit="coppe", denari_points=2))
    assert result.points == PlayerCounts(2, 0)
