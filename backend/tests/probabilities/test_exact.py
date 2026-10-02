from dataclasses import replace
from fractions import Fraction as F
import pytest

from engine.game_state import GameState
from engine.probabilities import (ProbabilityEngine, ProbabilityConfig, ProbabilityDistribution,
                                 WeightedWorld, PossibleWorld, EnumerationLimitExceeded, Region)

ENGINE = ProbabilityEngine()


def test_exact_six_worlds_equal_weight(small_state):
    dist=ENGINE.distribution(small_state,"exact")
    assert dist.exact and len(dist.worlds)==6 and dist.total_mass==1
    assert all(w.probability==F(1,6) for w in dist.worlds)
    for item in dist.worlds:
        dist.state.validate_world(item.world)


def test_enumeration_matches_analytic_counts(small_state):
    dist=ENGINE.distribution(small_state)
    for region in Region:
        pmf=ENGINE.matching_count_distribution(small_state,lambda c:c.rank==7,region)
        for k,p in enumerate(pmf):
            assert dist.probability(lambda w:sum(c.rank==7 for c in w.cards_in(region))==k)==p


def test_enumeration_matches_every_card_marginal(small_state,pool):
    dist=ENGINE.distribution(small_state)
    for card in pool:
        for region in Region:
            assert dist.probability(lambda w:card in w.cards_in(region))==ENGINE.card_probability(small_state,card,region)


def test_joint_opponent_and_draw_probability(small_state,pool):
    dist=ENGINE.distribution(small_state)
    assert dist.probability(lambda w:pool[0] in w.opponent_hand and pool[1] in w.draw_pile)==F(1,3)


def test_conditioning_bayes_changes_other_card_marginal(small_state,pool):
    dist=ENGINE.distribution(small_state).condition(lambda w:pool[0] in w.opponent_hand)
    assert len(dist.worlds)==3 and dist.total_mass==1 and dist.exact and dist.conditioned
    assert dist.probability(lambda w:pool[1] in w.opponent_hand)==F(1,3)
    assert dist.probability(lambda w:pool[1] in w.draw_pile)==F(2,3)


def test_impossible_evidence_rejected(small_state):
    with pytest.raises(ValueError):
        ENGINE.distribution(small_state).condition(lambda w:False)


def test_exact_limit_prevents_unbounded_enumeration(small_state):
    with pytest.raises(EnumerationLimitExceeded):
        ProbabilityEngine(ProbabilityConfig(max_exact_worlds=5)).distribution(small_state,"exact")


def test_exact_boundary_is_inclusive(small_state):
    assert ProbabilityEngine(ProbabilityConfig(max_exact_worlds=6)).distribution(small_state).exact


def test_partial_pool_world_count_and_assignments(small_state):
    dist=ENGINE.distribution(small_state.evolve(opponent_hand_size=1,draw_pile_size=1))
    assert len(dist.worlds)==12
    assert all(len(w.world.unassigned)==2 and w.probability==F(1,12) for w in dist.worlds)


def test_zero_unknowns_has_single_world():
    state=GameState(player_hand=GameState().deck.cards)
    dist=ENGINE.distribution(state)
    assert len(dist.worlds)==1 and dist.worlds[0].probability==1
    assert dist.worlds[0].world==PossibleWorld((),(),())


def test_known_opponent_identity_in_every_world(small_state,pool):
    dist=ENGINE.distribution(small_state.evolve(opponent_known_cards=(pool[0],)))
    assert len(dist.worlds)==3
    assert all(pool[0] in w.world.opponent_hand for w in dist.worlds)


def test_exact_estimate_has_no_sampling_error(small_state):
    result=ENGINE.distribution(small_state).estimate(lambda w:True)
    assert result.probability==1 and result.exact
    assert result.standard_error is None and result.sample_count is None


def test_bad_distribution_mass_rejected(small_state):
    dist=ENGINE.distribution(small_state)
    with pytest.raises(ValueError):
        replace(dist,worlds=dist.worlds[:1])


def test_duplicate_distribution_worlds_rejected(small_state):
    dist=ENGINE.distribution(small_state)
    item=WeightedWorld(dist.worlds[0].world,F(1,2))
    with pytest.raises(ValueError):
        replace(dist,worlds=(item,item))


def test_same_input_same_exact_distribution(small_state):
    assert ENGINE.distribution(small_state)==ENGINE.distribution(small_state)
