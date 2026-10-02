import ast
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.core.errors import RevisionConflict
from backend.app.services.repository import InMemoryGameRepository
from backend.app.services.serialization import state_to_wire
from engine.cards import Deck
from engine.decision_engine import DecisionEngine
from engine.game_state import CapturedCards, GameState, Player
from engine.simulation import SimulationEngine


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def risk_state():
    deck = Deck.create(); cards = {c.id:c for c in deck.cards}
    own = (cards['coppe:4'], cards['coppe:6'])
    table = (cards['denari:2'], cards['denari:3'])
    pool = (cards['spade:9'], cards['bastoni:10'])
    return GameState(player_hand=own, table_cards=table, opponent_hand_size=1,
        captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in own+table+pool),()),
        last_capture_player=Player.PLAYER)


def create(client, state=None):
    response = client.post('/api/games', json={'state':state_to_wire(state)} if state else {})
    assert response.status_code == 201, response.text
    return response.json()


def rational(value):
    from fractions import Fraction
    return Fraction(value['numerator'], value['denominator'])


def test_create_get_default_game(client):
    response=client.post('/api/games',json={})
    assert response.status_code==201
    game=response.json()
    assert response.headers['location']==f"/api/games/{game['id']}"
    assert len(game['state']['deck'])==40
    assert game['revision']==1 and not game['has_analysis'] and not game['has_simulation']
    assert client.get(response.headers['location']).json()==game


def test_create_get_explicit_state_roundtrip(client):
    state=risk_state()
    game=create(client,state)
    assert game['state']==state_to_wire(state)
    assert client.get(f"/api/games/{game['id']}").json()==game


def test_game_ids_unique_and_storage_isolated(client):
    a=create(client); b=create(client,risk_state())
    assert a['id']!=b['id']
    assert client.get(f"/api/games/{a['id']}").json()==a
    with TestClient(create_app()) as another:
        assert another.get(f"/api/games/{a['id']}").status_code==404


def test_state_replacement_and_optimistic_revision(client):
    game=create(client)
    url=f"/api/games/{game['id']}/state"
    response=client.post(url,json={'state':state_to_wire(risk_state()),'expected_revision':1})
    assert response.status_code==200 and response.json()['revision']==2
    assert response.json()['state']['player_hand']==['coppe:4','coppe:6']
    stale=client.post(url,json={'state':{},'expected_revision':1})
    assert stale.status_code==409 and stale.json()['detail']['code']=='revision_conflict'
    assert client.get(f"/api/games/{game['id']}").json()==response.json()


def test_analysis_known_expected_result_and_saved_get(client):
    game=create(client,risk_state()); base=f"/api/games/{game['id']}"
    response=client.post(base+'/analyze',json={'max_depth':2,'probability_method':'exact'})
    assert response.status_code==200,response.text
    result=response.json()
    assert len(result['all_moves'])==2
    assert result['recommended_move']['played_card']['id']=='coppe:6'
    assert rational(result['expected_value'])==rational({'numerator':1115,'denominator':336})
    play4=next(item for item in result['all_moves'] if item['move']['played_card']['rank']==4)
    assert rational(play4['opponent_scopa_probability'])==rational({'numerator':1,'denominator':2})
    assert result['probabilities']['world_count']==2 and result['probabilities']['exact']
    assert result['state_revision']==1 and result['explored_states']>0
    assert client.get(base+'/analysis').json()==result
    assert client.get(base).json()['has_analysis']
    assert client.get(base).json()['state']==game['state']


def test_all_three_captures_are_returned(client):
    cards={c.id:c for c in Deck.create().cards}
    state=GameState(player_hand=(cards['coppe:8'],),opponent_hand_size=1,
        table_cards=tuple(cards[f'denari:{r}'] for r in (1,2,3,5,7)))
    game=create(client,state)
    response=client.post(f"/api/games/{game['id']}/analyze",json={'max_depth':1})
    assert response.status_code==200,response.text
    captures={tuple(sorted(c['rank'] for c in item['move']['captured_cards'])) for item in response.json()['all_moves']}
    assert captures=={(1,7),(3,5),(1,2,5)}


def test_analysis_repeated_math_reproducible(client):
    game=create(client,risk_state()); url=f"/api/games/{game['id']}/analyze"
    a=client.post(url,json={'max_depth':2}).json(); b=client.post(url,json={'max_depth':2}).json()
    a.pop('calculation_time_seconds'); b.pop('calculation_time_seconds')
    assert a==b


def test_simulation_repeated_seed_and_engine_result(client):
    game=create(client,risk_state()); url=f"/api/games/{game['id']}/simulate"
    body={'iterations':23,'seed':123,'max_depth':2,'trace_limit':2,
        'move':{'played_card':'coppe:4','captured_cards':[]}}
    a=client.post(url,json=body); b=client.post(url,json=body)
    assert a.status_code==b.status_code==200,a.text
    first=a.json(); second=b.json()
    first.pop('calculation_time_seconds'); second.pop('calculation_time_seconds')
    assert first==second and first['iterations']==23 and first['state_revision']==1
    assert len(first['means'])==9 and len(first['proportions'])==4 and len(first['traces'])==2
    assert first['proportions'][0]['interval_method']=='wilson'
    assert client.get(f"/api/games/{game['id']}").json()['has_simulation']
    assert client.get(f"/api/games/{game['id']}").json()['state']==game['state']


def test_api_parallel_simulation_matches_serial(client):
    game=create(client,risk_state()); url=f"/api/games/{game['id']}/simulate"
    body={'iterations':17,'seed':4,'max_depth':2,'chunk_size':4}
    a=client.post(url,json=body); b=client.post(url,json={**body,'workers':2,'chunk_size':3})
    assert a.status_code==b.status_code==200,b.text
    assert a.json()['means']==b.json()['means']
    assert a.json()['proportions']==b.json()['proportions']


def test_new_state_invalidates_analysis_and_simulation(client):
    game=create(client,risk_state()); base=f"/api/games/{game['id']}"
    assert client.post(base+'/analyze',json={'max_depth':1}).status_code==200
    assert client.post(base+'/simulate',json={'iterations':1,'max_depth':1}).status_code==200
    updated=client.post(base+'/state',json={'state':{}})
    assert updated.status_code==200
    assert updated.json()['revision']==2
    assert not updated.json()['has_analysis'] and not updated.json()['has_simulation']
    assert client.get(base+'/analysis').status_code==404


@pytest.mark.parametrize('method,suffix,body',[('get','',None),('get','/analysis',None),
    ('post','/state',{'state':{}}),('post','/analyze',{}),('post','/simulate',{'iterations':1})])
def test_unknown_game_returns_404(client,method,suffix,body):
    kwargs={} if body is None else {'json':body}
    response=getattr(client,method)(f'/api/games/{uuid4()}{suffix}',**kwargs)
    assert response.status_code==404 and response.json()['detail']['code']=='game_not_found'


def test_missing_analysis_and_malformed_uuid(client):
    game=create(client)
    response=client.get(f"/api/games/{game['id']}/analysis")
    assert response.status_code==404 and response.json()['detail']['code']=='analysis_not_found'
    assert client.get('/api/games/not-a-uuid').status_code==422


@pytest.mark.parametrize('state',[
    {'player_hand':['unknown:8']},
    {'player_hand':['coppe:4','coppe:4']},
    {'player_hand':['coppe:4'],'table_cards':['coppe:4']},
    {'opponent_known_cards':['coppe:4'],'opponent_hand_size':0},
    {'opponent_hand_size':41},
    {'player_hand':['coppe:4'],'played_cards':['coppe:4']},
    {'scopa_count':{'player':-1}},
    {'turn_number':True},
    {'unexpected':1},
    {'deck':[]},
])
def test_invalid_state_returns_422(client,state):
    assert client.post('/api/games',json={'state':state}).status_code==422


def test_failed_update_leaves_previous_state_and_analysis(client):
    game=create(client,risk_state()); base=f"/api/games/{game['id']}"
    result=client.post(base+'/analyze',json={'max_depth':1}).json()
    response=client.post(base+'/state',json={'state':{'player_hand':['bad']}})
    assert response.status_code==422
    assert client.get(base).json()['revision']==1
    assert client.get(base+'/analysis').json()==result


@pytest.mark.parametrize('suffix,body',[('/analyze',{'max_depth':0}),('/analyze',{'probability_method':'bad'}),
    ('/simulate',{'iterations':0}),('/simulate',{'iterations':True}),('/simulate',{'iterations':1_000_001}),
    ('/simulate',{'workers':9}),('/simulate',{'confidence':1}),('/simulate',{'seed':'42'}),
    ('/simulate',{'trace_limit':101}),('/simulate',{'player_policy':'bad'}),('/simulate',{'junk':1})])
def test_request_validation_limits(client,suffix,body):
    game=create(client,risk_state())
    assert client.post(f"/api/games/{game['id']}{suffix}",json=body).status_code==422


@pytest.mark.parametrize('move',[{'played_card':'bad'}, {'played_card':'coppe:5'},
    {'played_card':'coppe:4','captured_cards':['denari:2']}])
def test_invalid_forced_simulation_move_rejected_by_engine(client,move):
    game=create(client,risk_state())
    response=client.post(f"/api/games/{game['id']}/simulate",json={'iterations':1,'move':move})
    assert response.status_code==422 and response.json()['detail']['code']=='invalid_engine_input'


def test_engine_resource_limits_are_explicit_and_do_not_save_partial_analysis(client):
    game=create(client,risk_state()); base=f"/api/games/{game['id']}"
    response=client.post(base+'/analyze',json={'max_nodes':1})
    assert response.status_code==429 and response.json()['detail']['code']=='calculation_limit_exceeded'
    response=client.post(base+'/analyze',json={'probability_method':'exact','max_exact_worlds':1})
    assert response.status_code==429
    assert client.get(base+'/analysis').status_code==404


def test_opponent_turn_analysis_engine_error(client):
    game=create(client,risk_state().evolve(current_player=Player.OPPONENT))
    response=client.post(f"/api/games/{game['id']}/analyze",json={})
    assert response.status_code==422


def test_terminal_scoring_through_both_api_calculations(client):
    deck=Deck.create(); cards={c.id:c for c in deck.cards}
    own=(cards['coppe:5'],); table=(cards['denari:2'],cards['denari:3'])
    state=GameState(player_hand=own,table_cards=table,
        captured_cards=CapturedCards((),tuple(c for c in deck.cards if c not in own+table)))
    game=create(client,state); base=f"/api/games/{game['id']}"
    analysis=client.post(base+'/analyze',json={})
    simulation=client.post(base+'/simulate',json={'iterations':5,'max_depth':1})
    assert analysis.status_code==simulation.status_code==200
    assert rational(analysis.json()['expected_value'])==-4
    assert rational(analysis.json()['scopa_probability'])==0
    metric=next(m for m in simulation.json()['means'] if m['name']=='expected_value')
    assert rational(metric['mean'])==-4 and metric['standard_error']==0


def test_empty_game_analysis_has_no_invented_move(client):
    game=create(client)
    result=client.post(f"/api/games/{game['id']}/analyze",json={})
    assert result.status_code==200,result.text
    assert result.json()['all_moves']==[] and result.json()['recommended_move'] is None


def test_engine_calls_are_delegated(client,monkeypatch):
    calls=[]; analysis=DecisionEngine.analyze; simulation=SimulationEngine.simulate
    def analyze_spy(self,state):
        calls.append(('analyze',state)); return analysis(self,state)
    def simulate_spy(self,state,move=None):
        calls.append(('simulate',state)); return simulation(self,state,move)
    monkeypatch.setattr(DecisionEngine,'analyze',analyze_spy)
    monkeypatch.setattr(SimulationEngine,'simulate',simulate_spy)
    game=create(client,risk_state()); base=f"/api/games/{game['id']}"
    assert client.post(base+'/analyze',json={'max_depth':1}).status_code==200
    assert client.post(base+'/simulate',json={'iterations':1,'max_depth':1}).status_code==200
    assert [name for name,state in calls]==['analyze','simulate']
    assert all(state==risk_state() for name,state in calls)


@pytest.mark.parametrize('kind',['analyze','simulate'])
def test_state_changed_during_calculation_returns_conflict(client,monkeypatch,kind):
    game=create(client,risk_state()); repository=client.app.state.game_service.repository
    engine=DecisionEngine if kind=='analyze' else SimulationEngine
    original=getattr(engine,kind)
    def changed(self,state,*args):
        result=original(self,state,*args)
        from uuid import UUID
        repository.replace_state(UUID(game['id']),GameState(),1)
        return result
    monkeypatch.setattr(engine,kind,changed)
    body={'max_depth':1} if kind=='analyze' else {'iterations':1,'max_depth':1}
    response=client.post(f"/api/games/{game['id']}/{kind}",json=body)
    assert response.status_code==409
    current=client.get(f"/api/games/{game['id']}").json()
    assert current['revision']==2 and not current['has_analysis'] and not current['has_simulation']


def test_repository_revision_compare_and_set_is_atomic():
    repository=InMemoryGameRepository(); game=repository.create(GameState())
    def update(_):
        try:
            return repository.replace_state(game.id,risk_state(),1).revision
        except RevisionConflict:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(update,range(2)))
    assert results.count(2)==1 and results.count('conflict')==1


def test_openapi_exposes_requested_endpoints_and_typed_results(client):
    schema=client.get('/openapi.json').json()
    assert set(schema['paths'])=={'/api/games','/api/games/{id}','/api/games/{id}/state',
        '/api/games/{id}/analyze','/api/games/{id}/simulate','/api/games/{id}/analysis'}
    assert 'AnalysisResponse' in schema['components']['schemas']
    assert 'SimulationResponse' in schema['components']['schemas']
    assert 'RationalSchema' in schema['components']['schemas']


def test_router_has_no_engine_imports():
    root=Path(__file__).resolve().parents[2]/'app'/'api'
    modules=list(root.glob('*.py'))
    assert root.is_dir() and modules
    for path in modules:
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or '').startswith('engine')
            if isinstance(node,ast.Import):
                assert all(not item.name.startswith('engine') for item in node.names)
