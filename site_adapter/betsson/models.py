"""Synthetic training format, NOT a verified Betsson.it payload schema."""
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from engine.decision_engine import AnalysisResult, MoveAnalysis
from engine.game_state import GameState, Player
from engine.moves import Move

Count = Annotated[int, Field(strict=True, ge=0)]
Positive = Annotated[int, Field(strict=True, ge=1)]
Identifier = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]


class GameStatus(StrEnum):
    ACTIVE = 'active'
    WAITING_DEAL = 'waiting_deal'
    FINISHED = 'finished'


class SnapshotModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always')


class Counts(SnapshotModel):
    player: Count
    opponent: Count


class Captures(SnapshotModel):
    player: tuple[Identifier, ...]
    opponent: tuple[Identifier, ...]


class SnapshotHistory(SnapshotModel):
    turn_number: Count
    actor: Player
    played_card: Identifier
    captured_cards: tuple[Identifier, ...] = ()


class MockSnapshot(SnapshotModel):
    # Required provenance/variant declarations describe this project's fixtures.
    # They are not evidence of origin or compatibility with an external website.
    format_version: Literal['scopa-training-v1']
    mode: Literal['offline_training']
    variant: Literal['standard_scopa']
    snapshot_id: Identifier
    game_status: GameStatus
    player_hand: tuple[Identifier, ...]
    table_cards: tuple[Identifier, ...]
    known_played_cards: tuple[Identifier, ...]
    opponent_known_cards: tuple[Identifier, ...] = ()
    captured_cards: Captures
    score: Counts
    scopa_count: Counts
    current_player: Player
    turn_number: Count
    round_number: Positive
    opponent_hand_size: Count
    draw_pile_size: Count
    last_capture_player: Player | None = None
    game_history: tuple[SnapshotHistory, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedObservation:
    snapshot_id: str
    game_status: GameStatus
    state: GameState


@dataclass(frozen=True, slots=True)
class AdapterResult:
    observation: ParsedObservation
    status: str
    analysis: AnalysisResult | None

    @property
    def game_state(self) -> GameState:
        return self.observation.state

    @property
    def legal_moves(self) -> tuple[Move, ...]:
        return self.analysis.legal_moves if self.analysis else ()

    @property
    def all_moves(self) -> tuple[MoveAnalysis, ...]:
        return self.analysis.all_moves if self.analysis else ()

    @property
    def recommended_move(self) -> Move | None:
        return self.analysis.recommended_move if self.analysis else None

    @property
    def expected_value(self) -> Fraction | None:
        return self.analysis.expected_value if self.analysis else None

    @property
    def scopa_probability(self) -> Fraction | None:
        return self.analysis.scopa_probability if self.analysis else None

    @property
    def primiera_value(self) -> Fraction | None:
        return self.analysis.primiera_value if self.analysis else None

    @property
    def sette_bello_value(self) -> Fraction | None:
        return self.analysis.sette_bello_value if self.analysis else None

    @property
    def opponent_expected_value(self) -> Fraction | None:
        return self.analysis.opponent_expected_value if self.analysis else None

    @property
    def calculation_time(self) -> float | None:
        return self.analysis.calculation_time if self.analysis else None
