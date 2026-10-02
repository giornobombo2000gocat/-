import json
from engine.game_tree import GameTree, SearchConfig, save_tree


def test_export_preserves_all_states_probabilities_depths_and_evaluations(move_then_deal,tmp_path):
    result=GameTree(SearchConfig(max_depth=2,cards_per_hand=1)).search(move_then_deal)
    path=tmp_path/"tree.json"
    save_tree(result,path)
    data=json.loads(path.read_text(encoding="utf-8"))
    assert data["node_count"]==5 and len(data["explored_states"])==5
    for exported,node in zip(data["explored_states"],result.explored_states,strict=True):
        assert exported["depth"]==node.depth
        assert exported["probability"]=={"numerator":node.probability.numerator,"denominator":node.probability.denominator}
        assert exported["evaluation_total"]=={"numerator":node.evaluation.total.numerator,"denominator":node.evaluation.total.denominator}
        assert len(exported["state"]["table_cards"])==len(node.state.table_cards)
    assert data["explored_states"][3]["state"]["opponent_known_cards"]==[]


def test_export_is_identical_on_repeated_input(final_two_turns,tmp_path):
    result=GameTree().search(final_two_turns)
    a,b=tmp_path/"a.json",tmp_path/"b.json"
    save_tree(result,a)
    save_tree(result,b)
    assert a.read_bytes()==b.read_bytes()
