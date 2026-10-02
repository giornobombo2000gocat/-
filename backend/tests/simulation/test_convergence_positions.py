from fractions import Fraction
import pytest

from examples.simulation_convergence import cases, manifest
from engine.simulation import SimulationConfig, SimulationEngine


@pytest.mark.parametrize('case',cases(),ids=lambda case:case.name)
def test_benchmark_position_has_exact_reference_and_valid_rollouts(case):
    engine=SimulationEngine(SimulationConfig(iterations=5,seed=123,max_depth=case.depth))
    exact=engine.exact_reference(case.state,case.move)
    simulation=engine.simulate(case.state,case.move)
    assert isinstance(dict(exact.metrics)['expected_value'],Fraction)
    assert simulation.iterations==5 and simulation.reached_depth==case.depth
    assert exact.explored_nodes>1
    assert manifest(case)['capture']==[c.id for c in case.move.captured_cards]
    low,high=simulation.expected_value.hoeffding_interval
    assert low<=float(dict(exact.metrics)['expected_value'])<=high


def test_ten_distinct_benchmark_states_or_initial_moves():
    positions=cases()
    assert len(positions)==10
    assert len({case.state for case in positions})==10


def test_batch_cache_matches_uncached_rollouts():
    from engine.game_tree import PositionEvaluator
    from engine.probabilities import ProbabilityState
    from engine.rules import RulesEngine
    from engine.simulation.rollout import BatchJob, run_batch, rollout
    for case in cases():
        config=SimulationConfig(iterations=17,seed=123,max_depth=case.depth,trace_limit=17)
        belief=ProbabilityState.from_game_state(case.state)
        batch=run_batch(BatchJob(case.state,belief,config,0,17,case.move))
        samples=[rollout(case.state,belief,config,i,case.move,RulesEngine(),PositionEvaluator()) for i in range(17)]
        assert batch.traces==tuple(sample[3] for sample in samples)
        assert batch.totals==tuple(sum((sample[0][j] for sample in samples),Fraction()) for j in range(9))
        assert batch.squares==tuple(sum((sample[0][j]**2 for sample in samples),Fraction()) for j in range(9))
        assert batch.successes==tuple(sum(sample[1][j] for sample in samples) for j in range(4))
