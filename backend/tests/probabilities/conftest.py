import pytest

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState


@pytest.fixture
def pool():
    cards = {c.id: c for c in Deck.create().cards}
    return tuple(cards[key] for key in ("denari:7", "coppe:7", "spade:2", "bastoni:3"))


@pytest.fixture
def small_state(pool):
    deck = Deck.create()
    return GameState(deck=deck, opponent_hand_size=2, draw_pile_size=2,
                     captured_cards=CapturedCards((), tuple(c for c in deck.cards if c not in pool)))
