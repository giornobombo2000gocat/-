import json
from engine.decision_engine import DecisionConfig, DecisionEngine, save_analysis
from engine.game_tree import SearchConfig


def test_export_includes_all_moves_and_each_metric(eight_position,tmp_path):
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1))).analyze(eight_position)
    path=tmp_path/"analysis.json"
    save_analysis(result,path)
    data=json.loads(path.read_text(encoding="utf-8"))
    assert len(data["all_moves"])==3
    for move in data["all_moves"]:
        assert all(key in move for key in ("evaluation","expected_value","scopa_probability","primiera_value","sette_bello_value","opponent_expected_value"))
    assert "calculation_time_seconds" not in data


def test_export_same_input_same_bytes(risk_position,tmp_path):
    engine=DecisionEngine()
    a,b=tmp_path/"a.json",tmp_path/"b.json"
    save_analysis(engine.analyze(risk_position),a)
    save_analysis(engine.analyze(risk_position),b)
    assert a.read_bytes()==b.read_bytes()


def test_optional_timing_metadata(eight_position,tmp_path):
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1))).analyze(eight_position)
    path=tmp_path/"analysis.json"
    save_analysis(result,path,include_timing=True)
    assert json.loads(path.read_text(encoding="utf-8"))["calculation_time_seconds"]>=0
