from collections.abc import Mapping
from typing import Any

from engine.cards import Deck, DeckConfig
from engine.game_state import CapturedCards, GameState, HistoryEntry, Player, PlayerCounts
from engine.rules import RulesEngine
from engine.scoring import ScoringEngine

from .models import GameStatus, MockSnapshot, ParsedObservation


class StateParseError(ValueError):
    """Training snapshot is incomplete or contradicts the standard engine state."""


class StateParser:
    """Convert explicitly declared offline fixtures; no site extraction or I/O."""
    def __init__(self):
        self.deck = Deck.create(DeckConfig())
        self._cards = {card.id: card for card in self.deck.cards}

    def snapshot(self, payload: MockSnapshot | Mapping[str, Any]) -> MockSnapshot:
        try:
            return MockSnapshot.model_validate(payload)
        except ValueError as error:
            raise StateParseError(str(error)) from error

    def parse(self, payload: MockSnapshot | Mapping[str, Any]) -> ParsedObservation:
        snapshot = self.snapshot(payload)
        def cards(ids):
            try:
                return tuple(self._cards[key] for key in ids)
            except KeyError as error:
                raise StateParseError(f'Unknown training card id: {error.args[0]}') from None
        try:
            state = GameState(deck=self.deck,
                player_hand=cards(snapshot.player_hand), table_cards=cards(snapshot.table_cards),
                played_cards=cards(snapshot.known_played_cards),
                opponent_known_cards=cards(snapshot.opponent_known_cards),
                captured_cards=CapturedCards(cards(snapshot.captured_cards.player), cards(snapshot.captured_cards.opponent)),
                player_score=snapshot.score.player, opponent_score=snapshot.score.opponent,
                scopa_count=PlayerCounts(snapshot.scopa_count.player, snapshot.scopa_count.opponent),
                current_player=snapshot.current_player, turn_number=snapshot.turn_number,
                round_number=snapshot.round_number, opponent_hand_size=snapshot.opponent_hand_size,
                draw_pile_size=snapshot.draw_pile_size, last_capture_player=snapshot.last_capture_player,
                game_history=tuple(HistoryEntry(h.turn_number,h.actor,self._cards[h.played_card],cards(h.captured_cards))
                    for h in snapshot.game_history))
            self._validate_status(snapshot.game_status, state)
        except (ValueError, KeyError) as error:
            raise StateParseError(str(error)) from error
        return ParsedObservation(snapshot.snapshot_id, snapshot.game_status, state)

    @staticmethod
    def _validate_status(status: GameStatus, state: GameState) -> None:
        if status == GameStatus.FINISHED:
            if not RulesEngine.round_finished(state):
                raise ValueError('Finished snapshot still has hands or undealt cards')
            # Delegate completed-round validation to the existing scoring engine.
            ScoringEngine().calculate_score(state)
        elif status == GameStatus.WAITING_DEAL:
            if state.player_hand or state.opponent_hand_size or not state.draw_pile_size:
                raise ValueError('Waiting-deal snapshot must have empty hands and undealt cards')
        elif RulesEngine.round_finished(state):
            raise ValueError('Active status contradicts a finished round')
        elif state.current_player == Player.PLAYER and not state.player_hand:
            raise ValueError('Active player turn has no player cards')
        elif state.current_player == Player.OPPONENT and not state.opponent_hand_size:
            raise ValueError('Active opponent turn has no opponent cards')
