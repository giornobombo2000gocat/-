import pytest
from engine.game_state import CapturedCards, PlayerCounts
from engine.scoring import calculate_primiera, score_primiera, ScoringConfig

SUITS = ("denari", "coppe", "spade", "bastoni")


@pytest.mark.parametrize("rank,value", [(1,16),(2,12),(3,13),(4,14),(5,15),(6,18),(7,21),(8,10),(9,10),(10,10)])
def test_primiera_rank_values(cards, rank, value):
    result = calculate_primiera(tuple(cards[f"{s}:{rank}"] for s in SUITS))
    assert result.eligible and result.value == 4 * value


def test_primiera_uses_best_of_each_suit_not_sum_of_pile(cards):
    pile = tuple(cards[f"{s}:{r}"] for s in SUITS for r in (1,6,7,10))
    result = calculate_primiera(pile)
    assert result.value == 84 and len(result.best_cards) == 4
    assert all(c.rank == 7 for c in result.best_cards)


def test_known_primiera_76_position(cards):
    result = calculate_primiera(tuple(cards[key] for key in ("denari:7", "coppe:7", "spade:1", "bastoni:6")))
    assert result.eligible and result.value == 76


def test_missing_suit_disqualifies_even_with_higher_partial_value(cards):
    player = tuple(cards[f"{s}:7"] for s in SUITS[:3])
    opponent = tuple(cards[f"{s}:8"] for s in SUITS)
    result = score_primiera(CapturedCards(player, opponent))
    assert result.player.value == 63 and result.opponent.value == 40
    assert result.player.missing_suits == ("bastoni",)
    assert not result.player.eligible and result.opponent.eligible
    assert result.category.points == PlayerCounts(0, 1)


def test_both_missing_suits_get_no_point(cards):
    result = score_primiera(CapturedCards((cards["denari:7"],), (cards["coppe:6"],)))
    assert result.category.points == PlayerCounts() and result.category.winner is None


def test_primiera_tie_gets_no_point(cards):
    a = tuple(cards[f"{s}:8"] for s in SUITS)
    b = tuple(cards[f"{s}:9"] for s in SUITS)
    result = score_primiera(CapturedCards(a, b))
    assert result.player.value == result.opponent.value == 40
    assert result.category.points == PlayerCounts()


def test_primiera_player_win_and_weight(cards):
    a = tuple(cards[f"{s}:7"] for s in SUITS)
    b = tuple(cards[f"{s}:6"] for s in SUITS)
    assert score_primiera(CapturedCards(a,b), ScoringConfig(primiera_points=2)).category.points == PlayerCounts(2,0)


def test_primiera_empty_pile():
    result = calculate_primiera(())
    assert result.value == 0 and not result.eligible and result.missing_suits == SUITS


def test_equal_values_choose_deterministically(cards):
    pile = (cards["denari:9"], cards["denari:8"])
    assert calculate_primiera(pile) == calculate_primiera(tuple(reversed(pile)))
    assert calculate_primiera(pile).best_cards == (cards["denari:8"],)


def test_primiera_rejects_duplicate_cards(cards):
    with pytest.raises(ValueError):
        calculate_primiera((cards["denari:7"],) * 2)
