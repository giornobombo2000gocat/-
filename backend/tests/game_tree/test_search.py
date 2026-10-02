from dataclasses import replace
from fractions import Fraction as F
import pytest

from engine.cards import Deck
from engine.game_state import GameState, CapturedCards, Player
from engine.game_tree import GameTree, SearchConfig, NodeKind, EdgeKind, SearchLimitExceeded
from engine.probabilities import ProbabilityConfig, ProbabilityEngine


def test_zero_depth_has_only_cutoff(final_two_turns):
    result=GameTree(SearchConfig(max_depth=0)).search(final_two_turns)
    assert result.node_count==1 and result.root.kind==NodeKind.CUTOFF
    assert result.root.stop_reason=="depth_limit" and result.reached_depth==0


def test_one_depth_keeps_all_player_moves(cards):
    state=GameState(player_hand=(cards["coppe:8"],),opponent_hand_size=1,
                    table_cards=tuple(cards[f"denari:{r}"] for r in (1,2,3,5,7)))
    result=GameTree(SearchConfig(max_depth=1)).search(state)
    assert len(result.root.children)==3 and result.node_count==4
    for i in result.root.children:
        node=result.explored_states[i]
        assert node.depth==1 and node.kind==NodeKind.CUTOFF and node.edge_kind==EdgeKind.PLAYER_MOVE
        assert node.probability==1 and node.branch_probability is None
        assert node.state==node.move.resulting_state


def test_two_depth_reaches_terminal_and_exact_final_score(final_two_turns):
    result=GameTree(SearchConfig(max_depth=2)).search(final_two_turns)
    assert result.node_count==3 and result.reached_depth==2
    leaf=result.explored_states[-1]
    assert leaf.kind==NodeKind.TERMINAL and leaf.stop_reason=="round_complete"
    assert leaf.evaluation.source=="terminal_score" and leaf.value==-4
    assert result.root.value==-4


def test_current_player_opponent_can_be_root(final_two_turns):
    state=final_two_turns.evolve(current_player=Player.OPPONENT)
    result=GameTree(SearchConfig(max_depth=1)).search(state)
    assert result.root.kind==NodeKind.OPPONENT
    assert result.explored_states[1].edge_kind==EdgeKind.OPPONENT_MOVE


def test_player_move_then_opponent_move_then_unknown_card(move_then_deal):
    result=GameTree(SearchConfig(max_depth=2,cards_per_hand=1)).search(move_then_deal)
    assert result.node_count==5
    assert [node.edge_kind for node in result.explored_states]==[
        EdgeKind.ROOT,EdgeKind.PLAYER_MOVE,EdgeKind.OPPONENT_MOVE,EdgeKind.UNKNOWN_CARD,EdgeKind.UNKNOWN_CARD]
    chance=result.explored_states[2]
    assert chance.kind==NodeKind.CHANCE and chance.depth==2
    assert len(chance.children)==2
    for i in chance.children:
        node=result.explored_states[i]
        assert node.depth==2 and node.kind==NodeKind.CUTOFF
        assert node.branch_probability==F(1,2) and node.probability==F(1,2)
        assert len(node.state.player_hand)==1 and node.state.opponent_hand_size==1
        assert node.state.opponent_known_cards==() and node.state.draw_pile_size==0
        assert node.drawn_card==node.state.player_hand[0]


def test_chance_weighted_value_is_hand_verifiable(move_then_deal):
    result=GameTree(SearchConfig(max_depth=2,cards_per_hand=1)).search(move_then_deal)
    chance=result.explored_states[2]
    leaves=[result.explored_states[i] for i in chance.children]
    assert chance.value==(leaves[0].value+leaves[1].value)/2
    assert result.root.value==chance.value


def test_three_card_deal_has_sequential_without_replacement_chance(cards):
    deck=Deck.create()
    pool=deck.cards[:6]
    state=GameState(draw_pile_size=6,captured_cards=CapturedCards(deck.cards[6:],()),last_capture_player=Player.PLAYER)
    result=GameTree(SearchConfig(max_depth=0)).search(state)
    assert result.node_count==1+6+30+120
    assert len(result.root.children)==6
    for node in result.explored_states:
        if not node.children:
            assert node.kind==NodeKind.CUTOFF and node.depth==0
            assert node.probability==F(1,120)
            assert len(node.state.player_hand)==3 and node.state.opponent_hand_size==3
            assert node.state.draw_pile_size==0 and node.state.opponent_known_cards==()
            world=node.belief.worlds[0].world
            assert set(world.opponent_hand).isdisjoint(node.state.player_hand)
            assert set(world.opponent_hand+node.state.player_hand)==set(pool)


def test_hidden_opponent_deal_preserves_multiple_assignments():
    deck=Deck.create()
    state=GameState(draw_pile_size=4,captured_cards=CapturedCards(deck.cards[4:],()))
    result=GameTree(SearchConfig(max_depth=0,cards_per_hand=1)).search(state)
    for i in result.root.children:
        node=result.explored_states[i]
        assert len(node.belief.worlds)==3
        assert all(item.probability==F(1,3) for item in node.belief.worlds)
        assert node.state.opponent_known_cards==() and node.state.opponent_hand_size==1
        assert node.state.draw_pile_size==2 and node.branch_probability==F(1,4)


def test_partial_final_round_is_marked_not_given_final_score():
    result=GameTree().search(GameState())
    assert result.root.kind==NodeKind.TERMINAL
    assert result.root.stop_reason=="partial_round_complete"
    assert result.root.evaluation.source=="heuristic"


def test_max_nodes_exceeded_raises_not_silent_truncation(move_then_deal):
    with pytest.raises(SearchLimitExceeded):
        GameTree(SearchConfig(max_nodes=2)).search(move_then_deal)


def test_max_belief_worlds_exceeded_raises(cards):
    state=GameState(opponent_hand_size=1)
    with pytest.raises(SearchLimitExceeded):
        GameTree(SearchConfig(max_belief_worlds=2)).search(state)


def test_hidden_deal_expansion_limit_is_enforced():
    deck=Deck.create()
    state=GameState(draw_pile_size=4,captured_cards=CapturedCards(deck.cards[4:],()))
    with pytest.raises(SearchLimitExceeded):
        GameTree(SearchConfig(max_depth=0,cards_per_hand=1,max_belief_worlds=2)).search(state)


def test_repeated_search_same_result_and_original_unchanged(final_two_turns):
    tree=GameTree(SearchConfig(max_depth=2))
    a=tree.search(final_two_turns)
    assert a==tree.search(final_two_turns)
    assert final_two_turns.turn_number==0 and len(final_two_turns.player_hand)==1
    assert a.unique_state_count<=a.node_count


def test_supplied_belief_must_match_observation(final_two_turns):
    belief=ProbabilityEngine().distribution(final_two_turns.evolve(draw_pile_size=0,opponent_known_cards=(),opponent_hand_size=1))
    with pytest.raises(ValueError):
        GameTree().search(final_two_turns,belief)


def test_custom_first_player_after_deal(move_then_deal):
    result=GameTree(SearchConfig(max_depth=2,cards_per_hand=1,first_player=Player.OPPONENT)).search(move_then_deal)
    assert all(result.explored_states[i].state.current_player==Player.OPPONENT for i in result.explored_states[2].children)


@pytest.mark.parametrize("kwargs", [{"max_depth":-1},{"max_depth":True},{"max_nodes":0},{"cards_per_hand":0},{"max_belief_worlds":0},{"probability_method":"bad"}])
def test_invalid_search_config(kwargs):
    with pytest.raises(ValueError):
        SearchConfig(**kwargs)


def test_odd_draw_pile_cannot_deal_equal_hands():
    deck=Deck.create()
    state=GameState(draw_pile_size=3,captured_cards=CapturedCards(deck.cards[3:],()))
    with pytest.raises(ValueError):
        GameTree(SearchConfig(max_depth=0)).search(state)


def test_monte_carlo_belief_marks_result_approximate(move_then_deal):
    tree=GameTree(SearchConfig(max_depth=2,cards_per_hand=1,probability_method="monte_carlo"),
                  probabilities=ProbabilityEngine(ProbabilityConfig(monte_carlo_samples=100,seed=42)))
    result=tree.search(move_then_deal)
    assert result.probability_method=="monte_carlo" and result.seed==42 and result.sample_count==100
    assert result==tree.search(move_then_deal)
    assert all(not node.belief.exact for node in result.explored_states)
