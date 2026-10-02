"""Run python -m examples.game_tree_positions --output game-tree-example.json."""
import argparse
from pathlib import Path

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState
from engine.game_tree import GameTree, SearchConfig, save_tree


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("game-tree-example.json"))
    args=parser.parse_args()
    deck=Deck.create()
    cards={c.id:c for c in deck.cards}
    active=tuple(cards[key] for key in ("coppe:4","spade:6","denari:7","bastoni:8"))
    state=GameState(player_hand=(active[0],),opponent_known_cards=(active[1],),opponent_hand_size=1,
                    draw_pile_size=2,captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),
                    last_capture_player="player")
    result=GameTree(SearchConfig(max_depth=2,cards_per_hand=1)).search(state)
    assert result.node_count==5 and result.reached_depth==2
    assert result==GameTree(SearchConfig(max_depth=2,cards_per_hand=1)).search(state)
    save_tree(result,args.output)
    print(f"Explored states={result.node_count}; depth={result.reached_depth}; method={result.probability_method}")
    for node in result.explored_states:
        event=node.move.played_card.id if node.move else node.drawn_card.id if node.drawn_card else "current state"
        print(f"id={node.id}; parent={node.parent_id}; edge={node.edge_kind}; event={event}; depth={node.depth}; "
              f"probability={node.probability}; evaluation={node.evaluation.total}; value={node.value}; "
              f"table={[c.id for c in node.state.table_cards]}; kind={node.kind}")
    print(f"PASS: exact chance weights=1/2 + 1/2; exported to {args.output}")


if __name__=="__main__":
    main()
