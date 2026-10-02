import pytest
from engine.game_state import CapturedCards, Player, PlayerCounts
from engine.scoring import ScoringConfig, score_sette_bello


@pytest.mark.parametrize("owner,points", [(Player.PLAYER, PlayerCounts(1, 0)), (Player.OPPONENT, PlayerCounts(0, 1))])
def test_sette_bello_ownership(cards, owner, points):
    seven = (cards["denari:7"],)
    captures = CapturedCards(seven if owner == Player.PLAYER else (), seven if owner == Player.OPPONENT else ())
    result = score_sette_bello(captures)
    assert result.winner == owner and result.points == points


def test_other_sevens_and_denari_are_not_sette_bello(cards):
    result = score_sette_bello(CapturedCards((cards["coppe:7"], cards["denari:6"]), (cards["spade:7"],)))
    assert result.winner is None and result.points == PlayerCounts()


def test_uncaptured_sette_bello_awards_nothing():
    assert score_sette_bello(CapturedCards()).points == PlayerCounts()


def test_sette_bello_identity_and_weight_configured(cards):
    config = ScoringConfig(denari_suit="coppe", sette_bello_rank=6, sette_bello_points=4)
    assert score_sette_bello(CapturedCards((cards["coppe:6"],), (cards["denari:7"],)), config).points == PlayerCounts(4, 0)
