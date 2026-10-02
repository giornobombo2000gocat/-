"""Run: python -m examples.probability_calculations --output probability-report.md."""
import argparse
from fractions import Fraction as F
from pathlib import Path

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState
from engine.probabilities import ProbabilityConfig, ProbabilityEngine, ProbabilityState, Region


def report() -> str:
    deck = Deck.create()
    cards = {c.id:c for c in deck.cards}
    a,b,c,d = (cards[key] for key in ("denari:7","coppe:7","spade:2","bastoni:3"))
    pool = (a,b,c,d)
    state = GameState(opponent_hand_size=2, draw_pile_size=2,
                      captured_cards=CapturedCards((), tuple(card for card in deck.cards if card not in pool)))
    engine = ProbabilityEngine()
    distribution = engine.distribution(state, "exact")
    lines = ["# Probability calculations", "", "Assumption: uniform hidden-card assignments, no behavioral inference.",
             "Unknown pool A=denari:7, B=coppe:7, C=spade:2, D=bastoni:3.",
             "36 other cards are captured and known. Opponent has 2 hidden cards; draw pile has 2.",
             "Unordered world count = C(4,2) * C(2,2) = 6.", "",
             "| Opponent hand | Draw pile | Exact probability |", "| --- | --- | --- |"]
    for item in distribution.worlds:
        lines.append(f"| {', '.join(card.id for card in item.world.opponent_hand)} | "
                     f"{', '.join(card.id for card in item.world.draw_pile)} | {item.probability} |")
    conditioned = distribution.condition(lambda world:a in world.opponent_hand)
    checks = [
        ("A in opponent hand", "3 favorable hands / 6 = 1/2", F(1,2), engine.card_probability(state,a)),
        ("Both sevens in opponent hand", "1 favorable hand / 6 = 1/6 (not 1/4)", F(1,6),engine.all_cards_probability(state,(a,b))),
        ("No seven in opponent hand", "C(2,0)C(2,2)/C(4,2) = 1/6", F(1,6),engine.matching_count_distribution(state,lambda card:card.rank==7)[0]),
        ("Exactly one seven in opponent hand", "C(2,1)C(2,1)/C(4,2) = 4/6", F(2,3),engine.matching_count_distribution(state,lambda card:card.rank==7)[1]),
        ("At least one seven in opponent hand", "1 - 1/6 = 5/6",F(5,6),engine.at_least_one_probability(state,lambda card:card.rank==7)),
        ("A in hand and B in draw pile", "2 favorable worlds / 6 = 1/3",F(1,3),distribution.probability(lambda world:a in world.opponent_hand and b in world.draw_pile)),
        ("B in hand given A in hand", "1 favorable remaining slot / 3 = 1/3",F(1,3),conditioned.probability(lambda world:b in world.opponent_hand)),
        ("B in draw pile given A in hand", "2 draw slots / 3 candidates = 2/3",F(2,3),conditioned.probability(lambda world:b in world.draw_pile)),
    ]
    draw3 = state.evolve(opponent_hand_size=1,draw_pile_size=3)
    checks += [
        ("A belongs to draw pile of size 3", "3 slots / 4 unknown cards = 3/4",F(3,4),engine.card_probability(draw3,a,Region.DRAW_PILE)),
        ("Next drawn card is A", "Uniform next-card identity among 4 unknown cards = 1/4",F(1,4),engine.next_draw_probability(draw3,lambda card:card==a)),
    ]
    early = GameState(player_hand=tuple(cards[f"coppe:{r}"] for r in (1,2,3)),
                      table_cards=tuple(cards[f"denari:{r}"] for r in (1,2,3,4)),
                      opponent_hand_size=3,draw_pile_size=30)
    checks += [
        ("Early game: Sette Bello in opponent hand", "3 / 33 = 1/11",F(1,11),engine.card_probability(early,a)),
        ("Early game: at least one seven in opponent hand", "1 - C(29,3)/C(33,3) = 1 - 3654/5456 = 901/2728",F(901,2728),engine.at_least_one_probability(early,lambda card:card.rank==7)),
        ("Early game: next drawn card is a seven", "4 / 33",F(4,33),engine.next_draw_probability(early,lambda card:card.rank==7)),
    ]
    lines += ["", "Early game: hand coppe 1,2,3; table denari 1,2,3,4; unknown N=33, four sevens, h=3, d=30.",
              "", "| Event | Manual calculation | Expected | Actual | Match |", "| --- | --- | --- | --- | --- |"]
    for label, formula, expected, actual in checks:
        assert expected == actual, f"{label}: {expected} != {actual}"
        lines.append(f"| {label} | {formula} | {expected} | {actual} | PASS |")
    mc_engine=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=20000,seed=123))
    sampled=mc_engine.distribution(state,"monte_carlo")
    assert sampled == mc_engine.distribution(state,"monte_carlo")
    estimate=sampled.estimate(lambda world:any(card.rank==7 for card in world.opponent_hand))
    lines += ["", f"Monte Carlo: samples={estimate.sample_count}, seed=123, exact=False.",
              f"P(at least one seven): exact=5/6; empirical={estimate.probability} "
              f"({float(estimate.probability):.8f}); plug-in standard error={estimate.standard_error:.8f}.",
              "Repeated input/config/seed produces an identical empirical distribution.", "",
              f"All {len(checks)} exact manual calculations matched. All 6 worlds have mass 1/6; total mass=1."]
    return "\n".join(lines)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=report()
    if args.output:
        args.output.write_text(result,encoding="utf-8")
    print(result)
