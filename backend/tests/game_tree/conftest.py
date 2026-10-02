import pytest

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState


@pytest.fixture
def cards():
    return {c.id:c for c in Deck.create().cards}


@pytest.fixture
def final_two_turns(cards):
    active=tuple(cards[key] for key in ("coppe:5","spade:9","denari:2","denari:3","denari:9"))
    deck=Deck.create()
    return GameState(player_hand=(active[0],),opponent_known_cards=(active[1],),opponent_hand_size=1,
                     table_cards=active[2:],captured_cards=CapturedCards((),tuple(c for c in deck.cards if c not in active)))


@pytest.fixture
def move_then_deal(cards):
    # One card each, then two cards to deal. Exact unknown worlds are A/B swap.
    active=tuple(cards[key] for key in ("coppe:4","spade:6","denari:7","bastoni:8"))
    deck=Deck.create()
    return GameState(player_hand=(active[0],),opponent_known_cards=(active[1],),opponent_hand_size=1,
                     draw_pile_size=2,captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),
                     last_capture_player="player")
