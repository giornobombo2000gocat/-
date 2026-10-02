"""Verified decisions: shorter Sette Bello capture and avoiding opponent Scopa."""
from pathlib import Path
import argparse

from engine.cards import Deck
from engine.decision_engine import DecisionConfig, DecisionEngine, save_analysis
from engine.game_state import CapturedCards, GameState, Player
from engine.game_tree import SearchConfig


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,default=Path("."))
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    deck=Deck.create()
    cards={c.id:c for c in deck.cards}
    sette=GameState(player_hand=(cards["coppe:8"],),opponent_hand_size=1,
        table_cards=tuple(cards[key] for key in ("denari:7","coppe:1","spade:2","bastoni:3","spade:5")))
    own=(cards["coppe:4"],cards["coppe:6"])
    table=(cards["denari:2"],cards["denari:3"])
    hidden=(cards["spade:9"],cards["bastoni:10"])
    active=own+table+hidden
    risk=GameState(player_hand=own,table_cards=table,opponent_hand_size=1,
        captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),last_capture_player=Player.PLAYER)
    cases=(
        ("sette",sette,DecisionConfig(search=SearchConfig(max_depth=1))),
        ("risk-depth1",risk,DecisionConfig(search=SearchConfig(max_depth=1))),
        ("risk-depth2",risk,DecisionConfig(search=SearchConfig(max_depth=2))),
    )
    lines=["# Decision Engine verified examples", "", "EV = expected player utility minus expected opponent utility.",
           "Cutoff utility is explicitly heuristic; opponent policy is uniform over legal actions per possible hand.", ""]
    results={}
    for name,state,config in cases:
        result=DecisionEngine(config).analyze(state)
        assert result==DecisionEngine(config).analyze(state)
        results[name]=result
        save_analysis(result,args.output_dir/f"decision-{name}.json")
        lines += [f"## {name}", "", f"Hand: {[c.id for c in state.player_hand]}; table: {[c.id for c in state.table_cards]}",
                  f"Depth: {result.search_depth}; explored nodes: {result.tree.node_count}; method: {result.probabilities.method}", "",
                  "| Play | Capture | Immediate evaluation | Expected value | Player utility | Opponent utility | P(player Scopa) | P(opponent Scopa) | Primiera strength | Sette Bello points | Recommended |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for item in result.all_moves:
            lines.append(f"| {item.move.played_card.id} | {', '.join(c.id for c in item.move.captured_cards) or 'discard'} | "
                         f"{item.evaluation.total} | {item.expected_value} | {item.player_expected_value} | {item.opponent_expected_value} | "
                         f"{item.scopa_probability} | {item.opponent_scopa_probability} | {item.primiera_value} | "
                         f"{item.sette_bello_value} | {'YES' if item.move==result.recommended_move else ''} |")
        lines.append("")
    assert len(results["sette"].recommended_move.captured_cards)==2
    assert "denari:7" in {c.id for c in results["sette"].recommended_move.captured_cards}
    assert results["risk-depth1"].recommended_move.played_card.rank==4
    assert results["risk-depth2"].recommended_move.played_card.rank==6
    lines += ["PASS: all legal moves compared; shorter Sette Bello capture preferred; lookahead changes recommendation to avoid opponent Scopa.",
              "Repeated input/config produces identical mathematical results and JSON. Timing is deliberately omitted from the deterministic reports."]
    report="\n".join(lines)
    (args.output_dir/"decision-report.md").write_text(report,encoding="utf-8")
    print(report)


if __name__=="__main__":
    main()
