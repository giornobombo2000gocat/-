from fractions import Fraction as F
import pytest

from engine.cards import Deck
from engine.game_state import GameState, CapturedCards, Player, PlayerCounts
from engine.game_tree import SearchConfig
from engine.decision_engine import DecisionConfig, DecisionEngine
from engine.scoring import ScoringEngine


@pytest.mark.parametrize("table,expected", [((2,3),1),((2,3,9),0),((5,),1)])
def test_immediate_scopa_probability(cards,table,expected):
    state=GameState(player_hand=(cards["coppe:5"],),table_cards=tuple(cards[f"denari:{r}"] for r in table),opponent_hand_size=1)
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1))).analyze(state)
    assert result.scopa_probability==expected


def test_primiera_strength_and_eligibility_are_distinct(sette_position):
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1))).analyze(sette_position)
    best=result.recommended_analysis
    assert best.primiera_value==37  # denari 7=21, coppe ace=16.
    assert best.primiera_eligible_probability==0  # Two suits still missing.
    assert best.expected_captured_cards==3  # Played 8 is captured too.


def test_final_score_expected_value_is_exact_and_last_scopa_excluded(cards):
    deck=Deck.create()
    own=cards["coppe:5"]
    table=(cards["denari:2"],cards["denari:3"])
    active=(own,)+table
    state=GameState(player_hand=(own,),table_cards=table,
                     captured_cards=CapturedCards((),tuple(c for c in deck.cards if c not in active)))
    result=DecisionEngine().analyze(state)
    assert result.expected_value==-4 and result.scopa_probability==0
    best=result.recommended_analysis
    assert best.player_expected_value==0 and best.opponent_expected_value==4
    assert best.terminal_probability==1 and best.expected_evaluation.source=="expected_terminal_score"
    assert result.reached_depth==1


def test_future_scopa_probability_is_calculated_from_paths(cards):
    deck=Deck.create()
    own=(cards["coppe:4"],cards["coppe:9"])
    pool=tuple(cards[key] for key in ("denari:5","spade:6","bastoni:2","denari:3"))
    active=own+pool
    state=GameState(player_hand=own,opponent_hand_size=1,draw_pile_size=2,
                     captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),
                     last_capture_player=Player.PLAYER)
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=3))).analyze(state)
    play4=next(item for item in result.all_moves if item.move.played_card.rank==4)
    assert not play4.move.creates_scopa
    # If opponent holds 5 (1/4), it discards onto 4; player's 9 sweeps 4+5.
    assert play4.scopa_probability==F(1,4) and play4.expected_scopa_count==F(1,4)
    assert sum(o.probability for o in play4.outcomes)==1


def test_sette_bello_already_owned_remains_value_one(cards):
    state=GameState(player_hand=(cards["coppe:4"],),opponent_hand_size=1,
                     captured_cards=CapturedCards((cards["denari:7"],),()))
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1))).analyze(state)
    assert result.sette_bello_value==1 and result.recommended_analysis.sette_bello_probability==1


def test_sette_bello_owned_by_opponent_does_not_become_player_value(cards):
    state=GameState(player_hand=(cards["coppe:4"],),opponent_hand_size=1,
                     captured_cards=CapturedCards((),(cards["denari:7"],)))
    result=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1))).analyze(state)
    assert result.sette_bello_value==0
    assert all(o.opponent_sette_bello_owned for o in result.recommended_analysis.outcomes)


def test_separate_side_utilities_reproduce_existing_evaluator(cards):
    from engine.game_tree import PositionEvaluator
    state=GameState(captured_cards=CapturedCards((cards["denari:7"],),(cards["coppe:6"],)),scopa_count=PlayerCounts(2,1))
    evaluator=PositionEvaluator()
    player,opponent=evaluator.evaluate_sides(state)
    assert player.total-opponent.total==evaluator.evaluate(state).total
