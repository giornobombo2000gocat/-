from fractions import Fraction as F
import pytest

from engine.game_state import GameState, CapturedCards, PlayerCounts
from engine.game_tree import EvaluationConfig, PositionEvaluator, GameTree
from engine.rules import RulesEngine, RulesConfig
from engine.scoring import ScoringEngine, ScoringConfig


def test_heuristic_components_have_explicit_fraction_weights(cards):
    state=GameState(captured_cards=CapturedCards((cards["denari:7"],),()),scopa_count=PlayerCounts(1,0))
    result=PositionEvaluator().evaluate(state)
    assert result.source=="heuristic"
    assert result.captured_cards==F(1,40) and result.denari==F(1,10)
    assert result.primiera==F(21,84) and result.sette_bello==1 and result.scopa==1
    assert result.total==F(19,8)


def test_configurable_evaluation_can_isolate_scopa(cards):
    config=EvaluationConfig(captured_cards=0,denari=0,sette_bello=0,primiera=0,previous_score=0,scopa=2)
    state=GameState(scopa_count=PlayerCounts(2,1),player_score=10)
    assert PositionEvaluator(config=config).evaluate(state).total==2


def test_terminal_evaluation_equals_real_cumulative_score_difference(final_two_turns):
    state=final_two_turns
    rules=RulesEngine()
    for _ in range(2):
        state=rules.get_legal_moves(state)[0].resulting_state
    state=state.evolve(player_score=5,opponent_score=2)
    evaluation=PositionEvaluator().evaluate(state)
    score=ScoringEngine().calculate_score(state).total_scores
    assert evaluation.source=="terminal_score"
    assert evaluation.total==score.player-score.opponent==-1


def test_invalid_evaluation_weight():
    with pytest.raises(ValueError):
        EvaluationConfig(scopa=-1)


def test_rules_scoring_scopa_weights_must_agree():
    with pytest.raises(ValueError):
        GameTree(rules=RulesEngine(RulesConfig(scopa_points=2)))
    assert GameTree(rules=RulesEngine(RulesConfig(scopa_points=2)),
                    evaluator=PositionEvaluator(scoring=ScoringEngine(ScoringConfig(scopa_points=2))))
