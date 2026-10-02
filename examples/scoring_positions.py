"""Fixed scoring snapshots with hand-calculated expectations, never computed from the engine."""
from dataclasses import dataclass
from pathlib import Path
import argparse

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState, PlayerCounts
from engine.scoring import ScoringEngine


@dataclass(frozen=True, slots=True)
class ExpectedScore:
    cards: tuple[int, int]
    cards_points: tuple[int, int]
    scopa: tuple[int, int]
    scopa_points: tuple[int, int]
    denari: tuple[int, int]
    denari_points: tuple[int, int]
    sette_bello: tuple[int, int]
    sette_bello_points: tuple[int, int]
    primiera: tuple[int, int]
    primiera_eligible: tuple[bool, bool]
    primiera_missing: tuple[tuple[str, ...], tuple[str, ...]]
    primiera_points: tuple[int, int]
    round_score: tuple[int, int]
    total_score: tuple[int, int]


@dataclass(frozen=True, slots=True)
class ScoringPosition:
    name: str
    description: str
    state: GameState
    expected: ExpectedScore


def fixed_positions() -> tuple[ScoringPosition, ...]:
    deck = Deck.create()

    def state(select, scopa=(0, 0), previous=(0, 0)):
        return GameState(deck=deck,
                         captured_cards=CapturedCards(tuple(c for c in deck.cards if select(c)),
                                                      tuple(c for c in deck.cards if not select(c))),
                         scopa_count=PlayerCounts(*scopa), player_score=previous[0], opponent_score=previous[1])

    return (
        ScoringPosition("P1", "Player owns ranks 1-7 in every suit; opponent owns 8-10.",
            state(lambda c: c.rank <= 7, (2,1), (4,8)),
            ExpectedScore((28,12),(1,0),(2,1),(2,1),(7,3),(1,0),(1,0),(1,0),
                          (84,40),(True,True),((),()),(1,0),(6,1),(10,9))),
        ScoringPosition("P2", "Player owns ranks 8-10 in every suit; opponent owns 1-7.",
            state(lambda c: c.rank >= 8, (1,2), (8,4)),
            ExpectedScore((12,28),(0,1),(1,2),(1,2),(3,7),(0,1),(0,1),(0,1),
                          (40,84),(True,True),((),()),(0,1),(1,6),(9,10))),
        ScoringPosition("P3", "Player owns ranks 1,2,3,6,8 in every suit; opponent owns the rest.",
            state(lambda c: c.rank in (1,2,3,6,8)),
            ExpectedScore((20,20),(0,0),(0,0),(0,0),(5,5),(0,0),(0,1),(0,1),
                          (72,84),(True,True),((),()),(0,1),(0,2),(0,2))),
        ScoringPosition("P4", "Player owns odd ranks in every suit; opponent owns even ranks.",
            state(lambda c: c.rank % 2 == 1, (1,1)),
            ExpectedScore((20,20),(0,0),(1,1),(1,1),(5,5),(0,0),(1,0),(1,0),
                          (84,72),(True,True),((),()),(1,0),(3,1),(3,1))),
        ScoringPosition("P5", "Player owns denari, coppe and spade; opponent owns all bastoni.",
            state(lambda c: c.suit != "bastoni"),
            ExpectedScore((30,10),(1,0),(0,0),(0,0),(10,0),(1,0),(1,0),(1,0),
                          (63,21),(False,False),(("bastoni",),("denari","coppe","spade")),(0,0),(3,0),(3,0))),
        ScoringPosition("P6", "Player owns all bastoni and rank 8 of each other suit; opponent owns the rest.",
            state(lambda c: c.suit == "bastoni" or c.rank == 8, (1,0)),
            ExpectedScore((13,27),(0,1),(1,0),(1,0),(1,9),(0,1),(0,1),(0,1),
                          (51,63),(True,False),((),("bastoni",)),(1,0),(2,3),(2,3))),
        ScoringPosition("P7", "Player owns 1,2,3,4,7 in denari/coppe and 1,2,3,4,6 in spade/bastoni; opponent owns the rest.",
            state(lambda c: c.rank in ((1,2,3,4,7) if c.suit in ("denari","coppe") else (1,2,3,4,6)), (1,2)),
            ExpectedScore((20,20),(0,0),(1,2),(1,2),(5,5),(0,0),(1,0),(1,0),
                          (78,78),(True,True),((),()),(0,0),(2,2),(2,2))),
    )


def actual_score(state: GameState) -> ExpectedScore:
    result = ScoringEngine().calculate_score(state)
    b = result.breakdown
    def pair(counts):
        return (counts.player, counts.opponent)
    return ExpectedScore(
        (b.captured_cards.player_value,b.captured_cards.opponent_value),pair(b.captured_cards.points),
        pair(b.scopa.counts),pair(b.scopa.points),
        (b.denari.player_value,b.denari.opponent_value),pair(b.denari.points),
        (b.sette_bello.player_value,b.sette_bello.opponent_value),pair(b.sette_bello.points),
        (b.primiera.player.value,b.primiera.opponent.value),
        (b.primiera.player.eligible,b.primiera.opponent.eligible),
        (b.primiera.player.missing_suits,b.primiera.opponent.missing_suits),pair(b.primiera.category.points),
        pair(result.round_points),pair(result.total_scores),
    )


def render_report() -> str:
    lines = ["# Fixed scoring positions", "", "All pairs are (player, opponent). Every position assigns all 40 cards.", ""]
    for position in fixed_positions():
        actual = actual_score(position.state)
        assert actual == position.expected, f"{position.name}: {actual} != {position.expected}"
        lines += [f"## {position.name}", "", position.description, ""]
        for label, values, points in (
            ("Cards captured",actual.cards,actual.cards_points), ("Scopa",actual.scopa,actual.scopa_points),
            ("Denari",actual.denari,actual.denari_points), ("Sette Bello",actual.sette_bello,actual.sette_bello_points),
            ("Primiera",actual.primiera,actual.primiera_points),
        ):
            lines.append(f"{label}: {values}; points: {points}  ")
        lines += [f"Primiera eligible: {actual.primiera_eligible}; missing suits: {actual.primiera_missing}  ",
                  f"Previous score: {(position.state.player_score,position.state.opponent_score)}  ",
                  f"Final score: round={actual.round_score}; total={actual.total_score}", "",
                  f"Expected: `{position.expected}`", "", f"Actual: `{actual}`", "", "**MATCH**", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = render_report()
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    print(report)
