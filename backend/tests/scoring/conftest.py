import pytest
from engine.cards import Deck


@pytest.fixture
def deck():
    return Deck.create()


@pytest.fixture
def cards(deck):
    return {c.id: c for c in deck.cards}
