from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as F
import pytest

from engine.cards import Deck, DeckConfig
from engine.decision_engine import DecisionEngine, DecisionConfig
from engine.game_state import GameState, Player, CapturedCards, PlayerCounts
from engine.game_tree import SearchConfig, EvaluationConfig, SearchLimitExceeded, PositionEvaluator
from engine.probabilities import ProbabilityConfig
from engine.rules import RulesEngine, RulesConfig
from engine.scoring import ScoringEngine, ScoringConfig


def shallow(**kwargs):
    return DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1),**kwargs))


def test_all_three_eight_combinations_are_analyzed(eight_position):
    result=shallow().analyze(eight_position)
    assert len(result.all_moves)==len(result.legal_moves)==3
    assert set(result.legal_moves)==set(RulesEngine().get_legal_moves(eight_position))
    assert {tuple(sorted(c.value for c in item.move.captured_cards)) for item in result.all_moves}=={(1,2,5),(1,7),(3,5)}
    assert result.status=="analyzed" and result.calculation_time>=0


def test_shorter_capture_with_sette_bello_beats_more_cards(sette_position):
    result=shallow().analyze(sette_position)
    best=result.recommended_analysis
    assert best is not None
    assert {c.id for c in best.move.captured_cards}=={"denari:7","coppe:1"}
    assert len(best.move.captured_cards)==2
    longer=next(item for item in result.all_moves if len(item.move.captured_cards)==3)
    assert best.expected_value>longer.expected_value
    assert best.sette_bello_value==best.sette_bello_probability==1
    assert longer.sette_bello_value==0


def test_recommendation_is_global_expected_value_maximum(eight_position):
    result=shallow().analyze(eight_position)
    assert result.expected_value==max(item.expected_value for item in result.all_moves)
    assert result.recommended_move in result.legal_moves
    assert result.expected_value==result.tree.root.value


def test_every_move_has_evaluation_and_separate_expected_utilities(eight_position):
    result=shallow().analyze(eight_position)
    for item in result.all_moves:
        assert item.evaluation==PositionEvaluator().evaluate(item.move.resulting_state)
        assert item.expected_evaluation.total==item.expected_value
        assert item.player_expected_value-item.opponent_expected_value==item.expected_value
        assert isinstance(item.expected_value,F)
        assert 0<=item.scopa_probability<=1 and 0<=item.sette_bello_probability<=1


def test_summary_fields_match_recommended_move(eight_position):
    result=shallow().analyze(eight_position)
    best=result.recommended_analysis
    assert (result.scopa_probability,result.primiera_value,result.sette_bello_value,result.opponent_expected_value)==(
        best.scopa_probability,best.primiera_value,best.sette_bello_value,best.opponent_expected_value)
    assert result.exact_probabilities is True


def test_deeper_search_avoids_opponent_scopa(risk_position):
    immediate=shallow().analyze(risk_position)
    future=DecisionEngine().analyze(risk_position)
    assert immediate.recommended_move.played_card.rank==4  # Immediate utilities tie.
    assert future.recommended_move.played_card.rank==6
    risky=next(item for item in future.all_moves if item.move.played_card.rank==4)
    safe=next(item for item in future.all_moves if item.move.played_card.rank==6)
    assert risky.opponent_scopa_probability==F(1,2)
    assert safe.opponent_scopa_probability==0
    assert safe.expected_value>risky.expected_value


def test_hand_checked_weighted_opponent_evaluation(risk_position):
    result=DecisionEngine().analyze(risk_position)
    for item in result.all_moves:
        assert len(item.outcomes)==2
        assert all(o.probability==F(1,2) for o in item.outcomes)
        expected_opponent=sum((o.opponent_evaluation.total for o in item.outcomes),F())/2
        expected_difference=sum((o.player_evaluation.total-o.opponent_evaluation.total for o in item.outcomes),F())/2
        assert item.opponent_expected_value==expected_opponent
        assert item.expected_value==expected_difference


def test_opponent_value_is_not_negated_net_value(risk_position):
    result=DecisionEngine().analyze(risk_position)
    assert result.opponent_expected_value>=0
    assert result.opponent_expected_value!=-result.expected_value


def test_tie_breaker_is_stable_card_identity(cards):
    state=GameState(player_hand=(cards["coppe:6"],cards["coppe:4"]),opponent_hand_size=1)
    result=shallow().analyze(state)
    assert len({item.expected_value for item in result.all_moves})==1
    assert result.recommended_move.played_card.id=="coppe:4"
    reordered=state.evolve(player_hand=tuple(reversed(state.player_hand)))
    assert shallow().analyze(reordered).recommended_move.played_card==result.recommended_move.played_card


def test_tie_between_same_card_captures_uses_stable_capture_ids(cards):
    state=GameState(player_hand=(cards["coppe:5"],),table_cards=(cards["denari:5"],cards["spade:5"]),opponent_hand_size=1)
    config=DecisionConfig(search=SearchConfig(max_depth=1),evaluation=EvaluationConfig(captured_cards=0,denari=0,primiera=0))
    result=DecisionEngine(config).analyze(state)
    assert result.recommended_move.captured_cards==(cards["denari:5"],)


def test_configurable_weights_change_recommendation(sette_position):
    # Isolate card count to verify configuration; defaults deliberately do not do this.
    config=DecisionConfig(search=SearchConfig(max_depth=1),evaluation=EvaluationConfig(scopa=0,denari=0,sette_bello=0,primiera=0,previous_score=0))
    result=DecisionEngine(config).analyze(sette_position)
    assert len(result.recommended_move.captured_cards)==3


def test_same_input_same_math_and_state_unchanged(risk_position):
    engine=DecisionEngine()
    first=engine.analyze(risk_position)
    assert first==engine.analyze(risk_position)  # Timing is nonmathematical metadata.
    assert risk_position.turn_number==0 and len(risk_position.player_hand)==2


def test_result_is_immutable(eight_position):
    result=shallow().analyze(eight_position)
    with pytest.raises(FrozenInstanceError):
        result.status="changed"


def test_no_moves_completed_round_has_no_invented_recommendation():
    result=DecisionEngine().analyze(GameState())
    assert result.all_moves==() and result.recommended_move is None
    assert result.expected_value is None and result.scopa_probability is None
    assert result.status=="round_finished"


def test_no_moves_pending_deal_is_explicit():
    result=DecisionEngine().analyze(GameState(draw_pile_size=6))
    assert result.status=="no_legal_moves" and result.tree is None
    assert result.legal_moves==() and result.opponent_expected_value is None


def test_opponent_turn_requires_explicitly_different_analysis(cards):
    with pytest.raises(ValueError):
        DecisionEngine().analyze(GameState(current_player=Player.OPPONENT,opponent_hand_size=1))


def test_wrong_input_type_rejected():
    with pytest.raises(TypeError):
        DecisionEngine().analyze({})


def test_depth_zero_cannot_skip_legal_moves():
    with pytest.raises(ValueError):
        DecisionConfig(search=SearchConfig(max_depth=0))


def test_resource_limit_propagates_without_partial_move_selection(eight_position):
    with pytest.raises(SearchLimitExceeded):
        DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1,max_nodes=2))).analyze(eight_position)


def test_all_outcomes_normalize_and_component_sum_matches(risk_position):
    result=DecisionEngine().analyze(risk_position)
    for item in result.all_moves:
        assert sum((o.probability for o in item.outcomes),F())==1
        assert item.expected_value==sum((o.probability*(o.player_evaluation.total-o.opponent_evaluation.total) for o in item.outcomes),F())


def test_probability_method_metadata_and_seed_are_preserved(risk_position):
    config=DecisionConfig(search=SearchConfig(max_depth=2,probability_method="monte_carlo"),
                          probabilities=ProbabilityConfig(monte_carlo_samples=500,seed=123))
    engine=DecisionEngine(config)
    result=engine.analyze(risk_position)
    assert result.exact_probabilities is False
    assert result.probabilities.seed==123 and result.probabilities.sample_count==500
    assert result==engine.analyze(risk_position)
    assert len(result.all_moves)==2


def test_custom_deck_scoring_supported():
    deck_config=DeckConfig(("gold","blue"),(1,2,3),(1,2,3))
    scoring=ScoringEngine(ScoringConfig(deck_config=deck_config,denari_suit="gold",sette_bello_rank=3,
                                      primiera_values=((1,16),(2,12),(3,13))))
    deck=Deck.create(deck_config)
    cards={c.id:c for c in deck.cards}
    state=GameState(deck=deck,player_hand=(cards["blue:3"],),table_cards=(cards["gold:1"],cards["gold:2"]),
                     opponent_hand_size=1)
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1)),scoring=scoring).analyze(state)
    assert result.scopa_probability==1 and result.primiera_value==29


def test_rules_scoring_scopa_mismatch_rejected():
    with pytest.raises(ValueError):
        DecisionEngine(rules=RulesEngine(RulesConfig(scopa_points=2)))


def test_cumulative_score_offsets_do_not_change_move_ranking(risk_position):
    original=DecisionEngine().analyze(risk_position)
    shifted=DecisionEngine().analyze(risk_position.evolve(player_score=7,opponent_score=2))
    assert original.recommended_move.played_card==shifted.recommended_move.played_card
    assert shifted.expected_value==original.expected_value+5


def test_old_scopa_does_not_count_as_new_probability(cards):
    state=GameState(player_hand=(cards["coppe:4"],),opponent_hand_size=1,
                    table_cards=(cards["denari:2"],cards["denari:3"]),scopa_count=PlayerCounts(3,2))
    result=shallow().analyze(state)
    assert result.scopa_probability==0 and result.recommended_analysis.expected_scopa_count==0
