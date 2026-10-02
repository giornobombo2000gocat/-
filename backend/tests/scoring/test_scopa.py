import pytest
from engine.game_state import PlayerCounts
from engine.scoring import ScoringConfig, score_scopa


@pytest.mark.parametrize("counts", [PlayerCounts(), PlayerCounts(3, 2), PlayerCounts(1, 1), PlayerCounts(0, 4)])
def test_each_scopa_scores_independently(counts):
    result = score_scopa(counts)
    assert result.counts == counts and result.points == counts


def test_scopa_weight():
    assert score_scopa(PlayerCounts(3, 2), ScoringConfig(scopa_points=2)).points == PlayerCounts(6, 4)


def test_zero_scopa_weight_disables_points():
    assert score_scopa(PlayerCounts(3, 2), ScoringConfig(scopa_points=0)).points == PlayerCounts()


def test_scopa_does_not_accept_unvalidated_counts():
    with pytest.raises(TypeError):
        score_scopa((1, 2))
