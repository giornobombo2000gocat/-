from collections.abc import Iterable, Mapping
from typing import Any, Protocol, runtime_checkable

from engine.decision_engine import DecisionEngine
from engine.game_state import GameState, Player

from .models import AdapterResult, GameStatus, MockSnapshot, ParsedObservation
from .state_parser import StateParser


@runtime_checkable
class BetssonAdapter(Protocol):
    """Read-only offline observation boundary; no website/action methods."""
    def read_snapshot(self) -> MockSnapshot: ...
    def observe(self) -> ParsedObservation: ...
    def get_game_state(self) -> GameState: ...
    def analyze(self) -> AdapterResult: ...


class MockBetssonAdapter:
    """Only synthetic in-memory fixtures, optionally replayed explicitly by tests.

    No browser, network, credentials, polling, site selectors or move submission.
    """
    def __init__(self, snapshots: Iterable[MockSnapshot | Mapping[str, Any]], *,
                 engine: DecisionEngine | None = None, parser: StateParser | None = None):
        self._parser = parser or StateParser()
        self._snapshots = tuple(self._parser.snapshot(payload) for payload in snapshots)
        if not self._snapshots:
            raise ValueError('At least one offline training snapshot is required')
        self._index = 0
        self._engine = engine or DecisionEngine()

    def read_snapshot(self) -> MockSnapshot:
        return self._snapshots[self._index]

    def observe(self) -> ParsedObservation:
        return self._parser.parse(self.read_snapshot())

    def get_game_state(self) -> GameState:
        return self.observe().state

    def next_snapshot(self) -> MockSnapshot:
        if self._index + 1 >= len(self._snapshots):
            raise StopIteration('Offline fixture sequence exhausted')
        self._index += 1
        return self.read_snapshot()

    def analyze(self) -> AdapterResult:
        observation = self.observe()
        if observation.game_status == GameStatus.FINISHED:
            return AdapterResult(observation, 'game_finished', None)
        if observation.game_status == GameStatus.WAITING_DEAL:
            return AdapterResult(observation, 'waiting_for_deal', None)
        if observation.state.current_player != Player.PLAYER:
            return AdapterResult(observation, 'waiting_for_opponent', None)
        analysis = self._engine.analyze(observation.state)
        return AdapterResult(observation, analysis.status, analysis)
