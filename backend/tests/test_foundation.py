from dataclasses import FrozenInstanceError

import pytest

from engine.cards import Card, Deck, DeckConfig
from engine.game_state import CapturedCards, GameState, HistoryEntry, Player, PlayerCounts


def test_standard_deck_has_40_cards():
    deck = Deck.create()
    assert len(deck.cards) == 40
    assert len({c.id for c in deck.cards}) == 40
    assert all(sum(c.suit == suit for c in deck.cards) == 10 for suit in DeckConfig().suits)
    assert all(c.rank == c.value for c in deck.cards)


def test_custom_deck_values():
    deck = Deck.create(DeckConfig(("a", "b"), (1, 2), (3, 7)))
    assert [(c.id, c.value) for c in deck.cards] == [("a:1", 3), ("a:2", 7), ("b:1", 3), ("b:2", 7)]


@pytest.mark.parametrize("kwargs", [{"id": ""}, {"suit": ""}, {"rank": 0}, {"value": -1}, {"rank": True}])
def test_card_rejects_invalid_fields(kwargs):
    with pytest.raises(ValueError):
        Card(**({"id": "a:1", "suit": "a", "rank": 1, "value": 1} | kwargs))


def test_card_is_immutable():
    with pytest.raises(FrozenInstanceError):
        Deck.create().cards[0].value = 5


@pytest.mark.parametrize("config", [dict(suits=("a", "a")), dict(ranks=(1, 1), values=(1, 2)), dict(values=(1,)), dict(suits=()), dict(values=(True,) * 10)])
def test_invalid_configuration(config):
    with pytest.raises(ValueError):
        DeckConfig(**config)


def test_config_copies_mutable_input():
    suits = ["a"]
    config = DeckConfig(suits, [1], [2])
    suits.append("b")
    assert config.suits == ("a",)


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError):
        Deck((Card("same", "a", 1, 1), Card("same", "b", 2, 2)))


def test_duplicate_physical_card_rejected():
    with pytest.raises(ValueError):
        Deck((Card("x", "a", 1, 1), Card("y", "a", 1, 1)))


def test_seeded_shuffle_is_reproducible():
    deck = Deck.create()
    assert deck.shuffle(42) == deck.shuffle(42)
    assert set(deck.shuffle(42).cards) == set(deck.cards)
    assert deck.shuffle(42) != deck.shuffle(43)
    assert deck.cards[0].id == "denari:1"


def test_shuffle_requires_seed():
    with pytest.raises(ValueError):
        Deck.create().shuffle(None)


def test_deal_preserves_order_and_original():
    deck = Deck.create()
    hand, rest = deck.deal(3)
    assert [c.id for c in hand] == ["denari:1", "denari:2", "denari:3"]
    assert rest.cards == deck.cards[3:]
    assert len(deck.cards) == 40


@pytest.mark.parametrize("count", [-1, 41, True, 1.5])
def test_invalid_deal(count):
    with pytest.raises(ValueError):
        Deck.create().deal(count)


def test_deal_boundaries():
    deck = Deck.create()
    assert deck.deal(0) == ((), deck)
    assert deck.deal(40) == (deck.cards, Deck(()))


def test_remove_known_and_unknown():
    deck = Deck.create()
    known = deck.cards[:3]
    assert deck.remove_known(known).cards == deck.cards[3:]
    assert deck.unknown_cards(known) == deck.cards[3:]
    assert len(deck.cards) == 40


@pytest.mark.parametrize("known", [(Card("foreign", "a", 1, 1),), (Card("denari:1", "denari", 1, 9),)])
def test_foreign_or_mismatched_card_rejected(known):
    with pytest.raises(ValueError):
        Deck.create().remove_known(known)


def test_known_position_and_hidden_information():
    deck = Deck.create()
    state = GameState(deck=deck, player_hand=deck.cards[:3], table_cards=deck.cards[3:7],
                      opponent_known_cards=deck.cards[7:8], opponent_hand_size=3, draw_pile_size=29)
    assert len(state.known_cards) == 8
    assert state.unknown_cards == deck.cards[8:]
    assert state.hidden_opponent_count == 2


def test_played_ledger_can_overlap_table_and_captured():
    cards = Deck.create().cards
    state = GameState(table_cards=(cards[0],), played_cards=cards[:2],
                      captured_cards=CapturedCards(player=(cards[1],)))
    assert len(state.known_cards) == 2
    assert len(state.unknown_cards) == 38


def test_state_copies_mutable_input():
    hand = [Deck.create().cards[0]]
    state = GameState(player_hand=hand)
    hand.clear()
    assert len(state.player_hand) == 1
    with pytest.raises(FrozenInstanceError):
        state.turn_number = 1


def test_controlled_state_replacement():
    state = GameState()
    changed = state.evolve(current_player=Player.OPPONENT, turn_number=1)
    assert state.turn_number == 0
    assert changed.turn_number == 1
    assert changed.current_player == Player.OPPONENT
    with pytest.raises(ValueError):
        state.evolve(turn_number=-1)


def test_overlapping_zones_rejected():
    card = Deck.create().cards[0]
    with pytest.raises(ValueError):
        GameState(player_hand=(card,), table_cards=(card,))


def test_played_card_in_hand_rejected():
    card = Deck.create().cards[0]
    with pytest.raises(ValueError):
        GameState(player_hand=(card,), played_cards=(card,))


def test_opponent_known_count_validation():
    with pytest.raises(ValueError):
        GameState(opponent_known_cards=Deck.create().cards[:2], opponent_hand_size=1)


def test_impossible_hidden_counts_rejected():
    with pytest.raises(ValueError):
        GameState(opponent_hand_size=3, draw_pile_size=38)


@pytest.mark.parametrize("changes", [{"round_number": 0}, {"player_score": -1}, {"opponent_score": True}, {"current_player": "third"}])
def test_invalid_state_fields(changes):
    with pytest.raises(ValueError):
        GameState(**changes)


def test_captured_ownership_is_exclusive():
    card = Deck.create().cards[0]
    with pytest.raises(ValueError):
        CapturedCards((card,), (card,))


def test_scopa_counts_validate():
    assert PlayerCounts(2, 1).player == 2
    with pytest.raises(ValueError):
        PlayerCounts(-1, 0)


def test_history_and_played_ledger():
    card = Deck.create().cards[0]
    event = HistoryEntry(0, Player.PLAYER, card)
    state = GameState(played_cards=(card,), table_cards=(card,), game_history=[event], turn_number=1)
    assert state.game_history == (event,)
    with pytest.raises(ValueError):
        GameState(game_history=(event,))


def test_history_order_rejected():
    a, b = Deck.create().cards[:2]
    with pytest.raises(ValueError):
        GameState(played_cards=(a, b), turn_number=2,
                  game_history=(HistoryEntry(1, Player.PLAYER, a), HistoryEntry(0, Player.OPPONENT, b)))
