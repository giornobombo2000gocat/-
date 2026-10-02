from fractions import Fraction as F
from random import getstate
import pytest

from engine.cards import Deck
from engine.game_state import GameState
from engine.probabilities import ProbabilityConfig, ProbabilityEngine


def test_same_seed_same_empirical_distribution(small_state):
    engine=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=2000,seed=42))
    a=engine.distribution(small_state,"monte_carlo")
    b=engine.distribution(small_state,"monte_carlo")
    assert a==b and not a.exact and a.total_mass==1
    assert a.sample_count==2000 and a.seed==42


def test_sampling_does_not_change_global_rng(small_state):
    before=getstate()
    ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=50)).distribution(small_state,"monte_carlo")
    assert getstate()==before


def test_empirical_sevens_estimate_matches_exact_with_fixed_seed(small_state):
    engine=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=20000,seed=123))
    dist=engine.distribution(small_state,"monte_carlo")
    estimate=dist.estimate(lambda w:any(c.rank==7 for c in w.opponent_hand))
    assert abs(float(estimate.probability-F(5,6)))<0.02
    assert not estimate.exact and estimate.sample_count==20000
    assert estimate.standard_error is not None and estimate.standard_error>0


def test_auto_selects_mc_above_world_limit(small_state):
    engine=ProbabilityEngine(ProbabilityConfig(max_exact_worlds=5,monte_carlo_samples=100,seed=7))
    assert engine.distribution(small_state).method=="monte_carlo"
    assert engine.card_probability(small_state,small_state.unknown_cards[0])==F(1,2)  # Marginal still exact.


def test_sampler_handles_known_opponent_and_unassigned(small_state,pool):
    state=small_state.evolve(opponent_known_cards=(pool[0],),draw_pile_size=1)
    dist=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=100)).distribution(state,"monte_carlo")
    for item in dist.worlds:
        dist.state.validate_world(item.world)
        assert pool[0] in item.world.opponent_hand and len(item.world.unassigned)==1


def test_canonical_pool_makes_mc_input_order_invariant(small_state):
    engine=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=100,seed=13))
    reordered=small_state.evolve(deck=Deck(tuple(reversed(small_state.deck.cards))))
    assert engine.distribution(small_state,"monte_carlo")==engine.distribution(reordered,"monte_carlo")


def test_conditioned_mc_does_not_claim_exactness_or_effective_standard_error(small_state):
    engine=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=1000))
    conditioned=engine.distribution(small_state,"monte_carlo").condition(lambda w:any(c.rank==7 for c in w.opponent_hand))
    estimate=conditioned.estimate(lambda w:True)
    assert not estimate.exact and estimate.standard_error is None


def test_unknown_method_rejected(small_state):
    with pytest.raises(ValueError):
        ProbabilityEngine().distribution(small_state,"random_choice")


def test_large_space_uses_sampling_without_materializing_exact_worlds():
    state=GameState(opponent_hand_size=10,draw_pile_size=30)
    engine=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=250,seed=123))
    dist=engine.distribution(state)
    assert dist.state.world_count==847660528  # C(40,10), over 847 million worlds.
    assert not dist.exact and len(dist.worlds)<=250 and dist.total_mass==1
    assert engine.card_probability(state,state.deck.cards[0])==F(1,4)
