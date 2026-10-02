from dataclasses import replace
from fractions import Fraction as F
import random

import pytest

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState, Player
from engine.rules import RulesEngine
from engine.simulation import SimulationConfig, SimulationEngine, save_simulation
from engine.simulation.statistics import mean_estimate, proportion_estimate


def position(future=False):
    deck=Deck.create()
    cards={c.id:c for c in deck.cards}
    own=tuple(cards[k] for k in (('coppe:4','coppe:9') if future else ('coppe:4','coppe:6')))
    table=() if future else (cards['denari:2'],cards['denari:3'])
    pool=tuple(cards[k] for k in (('denari:5','spade:6','bastoni:2','denari:3') if future else ('spade:9','bastoni:10')))
    active=own+table+pool
    return GameState(player_hand=own,table_cards=table,opponent_hand_size=1,draw_pile_size=2 if future else 0,
        captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),last_capture_player=Player.PLAYER)


def forced(state):
    return next(m for m in RulesEngine().get_legal_moves(state) if m.played_card.rank==4)


@pytest.mark.parametrize('field,value', [('iterations',0),('iterations',True),('workers',0),('chunk_size',0),
    ('max_depth',-1),('trace_limit',-1),('seed',True),('confidence',0),('confidence',1),
    ('confidence',float('nan')),('player_policy','invalid'),('max_exact_nodes',0),('max_exact_worlds',0)])
def test_invalid_config(field,value):
    with pytest.raises(ValueError):
        SimulationConfig(**{field:value})


def test_mean_statistics_manual():
    estimate=mean_estimate('x',2,F(4),F(10),(F(0),F(4)),.95)
    assert estimate.mean==2 and estimate.sample_variance==2 and estimate.standard_error==1
    assert estimate.confidence_interval==pytest.approx((.040036015459946,3.959963984540054))
    assert estimate.hoeffding_interval[0]<=2<=estimate.hoeffding_interval[1]


def test_one_sample_does_not_invent_variance():
    estimate=mean_estimate('x',1,F(2),F(4),(F(0),F(4)),.95)
    assert estimate.sample_variance is None and estimate.standard_error is None
    assert estimate.confidence_interval is None


@pytest.mark.parametrize('successes',[0,5,10])
def test_wilson_manual_and_endpoints(successes):
    estimate=proportion_estimate('x',10,successes,.95)
    assert estimate.probability==F(successes,10)
    low,high=estimate.confidence_interval
    assert 0<=low<=float(estimate.probability)<=high<=1
    assert high>low
    if successes==5:
        assert (low,high)==pytest.approx((.2365930905,.7634069095))


def test_higher_confidence_widens_interval():
    a=proportion_estimate('x',100,50,.95)
    b=proportion_estimate('x',100,50,.99)
    assert b.confidence_interval[0]<a.confidence_interval[0]
    assert b.confidence_interval[1]>a.confidence_interval[1]


def test_repeat_seed_and_global_rng_untouched():
    state=position()
    engine=SimulationEngine(SimulationConfig(iterations=61,seed=23,max_depth=2,trace_limit=4))
    before=random.getstate()
    a=engine.simulate(state,forced(state))
    assert a==engine.simulate(state,forced(state))
    assert random.getstate()==before
    assert len(a.traces)==4 and a.reached_depth==2


def test_different_seed_changes_sample_paths():
    state=position()
    cfg=SimulationConfig(iterations=31,max_depth=2,trace_limit=31)
    a=SimulationEngine(cfg).simulate(state,forced(state))
    b=SimulationEngine(replace(cfg,seed=1)).simulate(state,forced(state))
    assert a.traces!=b.traces


def test_parallel_and_chunk_independence(tmp_path):
    state=position(True)
    cfg=SimulationConfig(iterations=37,seed=314,max_depth=3,chunk_size=8,trace_limit=5)
    serial=SimulationEngine(cfg).simulate(state,forced(state))
    parallel=SimulationEngine(replace(cfg,workers=2,chunk_size=3)).simulate(state,forced(state))
    assert serial==parallel
    assert all(m.samples==37 for m in parallel.means)
    save_simulation(serial,tmp_path/'a.json')
    save_simulation(parallel,tmp_path/'b.json')
    assert (tmp_path/'a.json').read_bytes()==(tmp_path/'b.json').read_bytes()


def test_exact_risk_hand_calculation():
    state=position()
    result=SimulationEngine(SimulationConfig(max_depth=2)).exact_reference(state,forced(state))
    assert dict(result.metrics)['expected_value']==F(467,168)
    assert dict(result.probabilities)['opponent_scopa']==F(1,2)
    assert dict(result.probabilities)['player_scopa']==0


def test_exact_future_scopa_hand_calculation():
    state=position(True)
    exact=SimulationEngine(SimulationConfig(max_depth=3)).exact_reference(state,forced(state))
    assert dict(exact.probabilities)['player_scopa']==F(1,4)
    assert dict(exact.metrics)['new_scopa_count']==F(1,4)


@pytest.mark.parametrize('future',[False,True])
def test_monte_carlo_converges_to_exact(future):
    state=position(future)
    result=SimulationEngine(SimulationConfig(iterations=2000,seed=123,max_depth=3 if future else 2)).compare_exact(state,forced(state))
    for item in result.comparisons:
        if item.name in ('expected_value','player_scopa','opponent_scopa'):
            assert float(item.absolute_error)<.06
    assert result.simulation.expected_value.hoeffding_interval[0]<=float(dict(result.exact.metrics)['expected_value'])<=result.simulation.expected_value.hoeffding_interval[1]


def test_terminal_score_and_final_scopa_rule():
    deck=Deck.create(); cards={c.id:c for c in deck.cards}
    own=(cards['coppe:5'],); table=(cards['denari:2'],cards['denari:3'])
    state=GameState(player_hand=own,table_cards=table,captured_cards=CapturedCards((),tuple(c for c in deck.cards if c not in own+table)))
    result=SimulationEngine(SimulationConfig(iterations=7,max_depth=1)).compare_exact(state)
    assert result.simulation.expected_value.mean==-4
    assert result.simulation.expected_value.standard_error==0
    assert result.simulation.scopa_probability.probability==0
    assert result.simulation.event('terminal').probability==1
    assert all(item.absolute_error==0 for item in result.comparisons)


def test_depth_zero_and_invalid_forced_move():
    state=position()
    engine=SimulationEngine(SimulationConfig(iterations=3,max_depth=0))
    result=engine.simulate(state)
    assert result.reached_depth==0 and result.scopa_probability.probability==0
    with pytest.raises(ValueError):
        engine.simulate(state,forced(state))


@pytest.mark.parametrize('policy',['greedy','first_legal'])
def test_policy_exact_agrees_on_deterministic_first_turn(policy):
    state=position()
    result=SimulationEngine(SimulationConfig(iterations=3,max_depth=1,player_policy=policy)).compare_exact(state)
    assert all(item.absolute_error==0 for item in result.comparisons)


def test_known_opponent_card_is_not_resampled():
    state=position(); card=next(c for c in state.deck.cards if c.id=='spade:9')
    state=state.evolve(opponent_known_cards=(card,))
    result=SimulationEngine(SimulationConfig(iterations=4,max_depth=2,trace_limit=4)).simulate(state,forced(state))
    assert all(t.events[1].move.played_card==card for t in result.traces)


def test_dealing_at_cutoff_matches_exact_and_keeps_opponent_hidden():
    deck=Deck.create(); cards={c.id:c for c in deck.cards}
    own=(cards['coppe:4'],); opponent=(cards['spade:6'],)
    pool=(cards['denari:7'],cards['bastoni:8'])
    active=own+opponent+pool
    state=GameState(player_hand=own,opponent_known_cards=opponent,opponent_hand_size=1,draw_pile_size=2,
        captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),last_capture_player=Player.PLAYER)
    result=SimulationEngine(SimulationConfig(iterations=10,max_depth=2,trace_limit=10)).compare_exact(state)
    assert all(item.absolute_error==0 for item in result.comparisons)
    for trace in result.simulation.traces:
        assert trace.events[-1].kind=='deal'
        assert len(trace.final_state.player_hand)==1
        assert trace.final_state.opponent_hand_size==1
        assert trace.final_state.opponent_known_cards==()
        assert trace.final_state.draw_pile_size==0


def test_odd_deal_is_rejected():
    state=GameState(draw_pile_size=1)
    with pytest.raises(ValueError,match='even'):
        SimulationEngine(SimulationConfig(iterations=1,max_depth=0)).simulate(state)
