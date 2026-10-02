import pytest

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState, Player


@pytest.fixture
def cards():
    return {c.id:c for c in Deck.create().cards}


@pytest.fixture
def eight_position(cards):
    return GameState(player_hand=(cards["coppe:8"],),opponent_hand_size=1,
                     table_cards=tuple(cards[f"denari:{r}"] for r in (1,2,3,5,7)))


@pytest.fixture
def sette_position(cards):
    # 8 can capture 1+7, 1+2+5, or 3+5. Sette Bello favors the shorter capture.
    return GameState(player_hand=(cards["coppe:8"],),opponent_hand_size=1,
                     table_cards=tuple(cards[key] for key in ("denari:7","coppe:1","spade:2","bastoni:3","spade:5")))


@pytest.fixture
def risk_position(cards):
    deck=Deck.create()
    own=(cards["coppe:4"],cards["coppe:6"])
    table=(cards["denari:2"],cards["denari:3"])
    hidden=(cards["spade:9"],cards["bastoni:10"])
    active=own+table+hidden
    return GameState(player_hand=own,table_cards=table,opponent_hand_size=1,
                     captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),
                     last_capture_player=Player.PLAYER)
