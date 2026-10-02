import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction as F
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from engine.cards import Deck
from engine.decision_engine import DecisionConfig, DecisionEngine
from engine.game_state import CapturedCards, GameState, Player, PlayerCounts
from engine.game_tree import SearchConfig, SearchLimitExceeded
from engine.rules import RulesEngine
from site_adapter.betsson import BetssonAdapter, MockBetssonAdapter, MockSnapshot, StateParser, StateParseError
from .conftest import snapshot_for


def test_snapshot_to_standard_game_state_preserves_all_fields(risk_state,risk_snapshot):
    observation=StateParser().parse(risk_snapshot)
    assert type(observation.state) is GameState
    assert observation.state==risk_state
    assert observation.snapshot_id=='training-001'
    assert observation.game_status=='active'


def test_known_and_unknown_information_stays_separate(risk_snapshot):
    state=MockBetssonAdapter([risk_snapshot]).get_game_state()
    assert {c.id for c in state.unknown_cards}=={'spade:9','bastoni:10'}
    assert state.opponent_known_cards==() and state.hidden_opponent_count==1
    assert len(state.captured_cards.player)==34


def test_adapter_matches_direct_decision_engine(risk_state,risk_snapshot):
    result=MockBetssonAdapter([risk_snapshot]).analyze()
    direct=DecisionEngine().analyze(risk_state)
    assert result.analysis==direct
    assert result.game_state==risk_state
    assert result.recommended_move==direct.recommended_move
    assert result.legal_moves==direct.legal_moves
    assert result.all_moves==direct.all_moves
    assert result.expected_value==F(1115,336)
    assert result.recommended_move.played_card.id=='coppe:6'
    assert result.scopa_probability==direct.scopa_probability
    assert result.primiera_value==direct.primiera_value
    assert result.sette_bello_value==direct.sette_bello_value
    assert result.opponent_expected_value==direct.opponent_expected_value
    assert result.calculation_time==result.analysis.calculation_time
    assert result.calculation_time>=0


def test_both_legal_moves_have_exact_expected_metrics(risk_snapshot):
    result=MockBetssonAdapter([risk_snapshot]).analyze()
    values={item.move.played_card.rank:item for item in result.all_moves}
    assert values[4].expected_value==F(467,168)
    assert values[4].opponent_scopa_probability==F(1,2)
    assert values[6].expected_value==F(1115,336)
    assert values[6].opponent_scopa_probability==0


def test_three_eight_combinations_are_preserved():
    cards={c.id:c for c in Deck.create().cards}
    state=GameState(player_hand=(cards['coppe:8'],),opponent_hand_size=1,
        table_cards=tuple(cards[f'denari:{r}'] for r in (1,2,3,5,7)))
    engine=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1)))
    result=MockBetssonAdapter([snapshot_for(state)],engine=engine).analyze()
    captures={tuple(sorted(c.rank for c in move.captured_cards)) for move in result.legal_moves}
    assert captures=={(1,7),(3,5),(1,2,5)}
    assert len(result.all_moves)==3


def test_sette_bello_is_preferred_over_more_captured_cards():
    cards={c.id:c for c in Deck.create().cards}
    state=GameState(player_hand=(cards['coppe:8'],),opponent_hand_size=1,
        table_cards=tuple(cards[k] for k in ('denari:7','coppe:1','spade:2','bastoni:3','spade:5')))
    result=MockBetssonAdapter([snapshot_for(state)],engine=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=1)))).analyze()
    assert len(result.recommended_move.captured_cards)==2
    assert 'denari:7' in {c.id for c in result.recommended_move.captured_cards}


def test_analysis_is_repeatable_and_never_advances_or_mutates(risk_snapshot):
    original=deepcopy(risk_snapshot)
    adapter=MockBetssonAdapter([risk_snapshot])
    before=adapter.get_game_state()
    assert adapter.analyze()==adapter.analyze()
    assert adapter.get_game_state()==before
    assert risk_snapshot==original and adapter.read_snapshot().snapshot_id=='training-001'


def test_snapshot_copies_mutable_input(risk_snapshot):
    adapter=MockBetssonAdapter([risk_snapshot])
    risk_snapshot['player_hand'].clear()
    risk_snapshot['score']['player']=999
    assert len(adapter.get_game_state().player_hand)==2
    assert adapter.get_game_state().player_score==0


def test_snapshot_and_observation_are_immutable(risk_snapshot):
    adapter=MockBetssonAdapter([risk_snapshot])
    with pytest.raises(ValidationError):
        adapter.read_snapshot().turn_number=8
    with pytest.raises(FrozenInstanceError):
        adapter.observe().snapshot_id='changed'


def test_explicit_fixture_replay_and_exhaustion(risk_state):
    rules=RulesEngine(); move=next(m for m in rules.get_legal_moves(risk_state) if m.played_card.rank==6)
    first=snapshot_for(risk_state,snapshot_id='one')
    second=snapshot_for(move.resulting_state,snapshot_id='two')
    adapter=MockBetssonAdapter([first,second])
    assert adapter.read_snapshot().snapshot_id=='one'
    adapter.analyze()
    assert adapter.read_snapshot().snapshot_id=='one'
    assert adapter.next_snapshot().snapshot_id=='two'
    assert adapter.get_game_state()==move.resulting_state
    with pytest.raises(StopIteration):
        adapter.next_snapshot()
    assert adapter.read_snapshot().snapshot_id=='two'


@pytest.mark.parametrize('status',['waiting_for_opponent','waiting_for_deal','game_finished'])
def test_non_actionable_states_never_call_decision_engine(risk_state,status):
    if status=='waiting_for_opponent':
        state=risk_state.evolve(current_player=Player.OPPONENT); external='active'
    elif status=='waiting_for_deal':
        state=GameState(draw_pile_size=2); external='waiting_deal'
    else:
        state=GameState(captured_cards=CapturedCards(Deck.create().cards,())); external='finished'
    class RejectCall(DecisionEngine):
        def analyze(self,state):
            raise AssertionError('Engine must not invent a player action')
    result=MockBetssonAdapter([snapshot_for(state,status=external)],engine=RejectCall()).analyze()
    assert result.status==status and result.analysis is None
    assert result.recommended_move is None and result.legal_moves==()
    assert result.expected_value is None and result.scopa_probability is None
    assert result.primiera_value is None and result.sette_bello_value is None
    assert result.calculation_time is None


def test_score_turn_history_and_played_cards_are_preserved(risk_state):
    move=RulesEngine().get_legal_moves(risk_state)[0]
    successor=move.resulting_state.evolve(player_score=5,opponent_score=3,round_number=2,scopa_count=PlayerCounts(2,1))
    parsed=StateParser().parse(snapshot_for(successor))
    assert parsed.state==successor
    assert parsed.state.game_history==successor.game_history
    assert parsed.state.played_cards==successor.played_cards


@pytest.mark.parametrize('missing',['format_version','mode','variant','game_status','player_hand',
    'table_cards','known_played_cards','captured_cards','score','scopa_count','current_player',
    'turn_number','round_number','opponent_hand_size','draw_pile_size'])
def test_missing_information_is_not_guessed(risk_snapshot,missing):
    risk_snapshot.pop(missing)
    with pytest.raises(StateParseError,match=missing):
        StateParser().parse(risk_snapshot)


@pytest.mark.parametrize('field,value',[
    ('mode','live'),('format_version','unknown'),('variant','unknown'),('game_status','paused'),
    ('snapshot_id',' '),('current_player','unknown'),('turn_number',True),('opponent_hand_size','1'),
    ('round_number',0),('draw_pile_size',-1),('player_hand',['not-a-card']),
    ('player_hand',['coppe:4','coppe:4']),('table_cards',['coppe:4']),
    ('known_played_cards',['coppe:4']),('opponent_known_cards',['spade:9','bastoni:10']),
    ('draw_pile_size',3),('game_status','finished'),('game_status','waiting_deal'),
    ('score',{'player':-1,'opponent':0}),('scopa_count',{'player':0,'opponent':False}),
])
def test_invalid_snapshot_rejected_without_partial_analysis(risk_snapshot,field,value):
    risk_snapshot[field]=value
    with pytest.raises(StateParseError):
        MockBetssonAdapter([risk_snapshot]).analyze()


def test_unrecognized_payload_fields_rejected(risk_snapshot):
    risk_snapshot['unrecognized_field']='value'
    with pytest.raises(StateParseError,match='unrecognized_field'):
        StateParser().parse(risk_snapshot)


def test_finished_snapshot_requires_complete_engine_scoring_information():
    with pytest.raises(StateParseError):
        StateParser().parse(snapshot_for(GameState(),status='finished'))


def test_active_status_with_empty_hands_is_inconsistent():
    with pytest.raises(StateParseError):
        StateParser().parse(snapshot_for(GameState()))


def test_empty_replay_is_rejected():
    with pytest.raises(ValueError,match='At least one'):
        MockBetssonAdapter([])


def test_engine_resource_errors_propagate(risk_snapshot):
    adapter=MockBetssonAdapter([risk_snapshot],engine=DecisionEngine(DecisionConfig(search=SearchConfig(max_nodes=1))))
    with pytest.raises(SearchLimitExceeded):
        adapter.analyze()


def test_adapter_has_no_site_or_action_methods(risk_snapshot):
    adapter=MockBetssonAdapter([risk_snapshot])
    assert isinstance(adapter,BetssonAdapter)
    assert not hasattr(adapter,'apply_move') and not hasattr(adapter,'submit_move')
    assert not hasattr(adapter,'connect') and not hasattr(adapter,'login')


def test_offline_analysis_never_uses_network(risk_snapshot,monkeypatch):
    import socket
    import http.client
    def forbidden(*args,**kwargs):
        raise AssertionError('Offline adapter must not access network')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(http.client.HTTPConnection,'request',forbidden)
    assert MockBetssonAdapter([risk_snapshot]).analyze().recommended_move.played_card.id=='coppe:6'


def test_engine_imports_without_adapters_backend_or_pydantic():
    script="import sys; from engine.decision_engine import DecisionEngine; assert not any(n.startswith(('site_adapter','backend','pydantic')) for n in sys.modules)"
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_dependency_direction_stays_adapter_to_engine():
    root=Path(__file__).resolve().parents[3]
    for path in (root/'engine').rglob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or '').startswith('site_adapter')
            if isinstance(node,ast.Import):
                assert all(not item.name.startswith('site_adapter') for item in node.names)
