from fractions import Fraction as F
import pytest

from engine.cards import Deck
from engine.game_state import GameState, CapturedCards, Player
from engine.game_tree import GameTree, SearchConfig
from engine.probabilities import ProbabilityEngine


def test_hidden_opponent_single_card_actions_are_all_enumerated(cards):
    deck=Deck.create()
    pool=tuple(cards[key] for key in ("coppe:5","coppe:4"))
    active=pool+(cards["spade:9"],cards["denari:2"],cards["denari:3"])
    state=GameState(player_hand=(cards["spade:9"],),table_cards=(cards["denari:2"],cards["denari:3"]),
                    opponent_hand_size=1,draw_pile_size=1,current_player=Player.OPPONENT,
                    captured_cards=CapturedCards((),tuple(c for c in deck.cards if c not in active)))
    result=GameTree(SearchConfig(max_depth=1)).search(state)
    assert len(result.root.children)==2
    for i in result.root.children:
        node=result.explored_states[i]
        assert node.branch_probability==F(1,2)
        assert node.state.opponent_hand_size==0
        assert node.move.played_card not in node.belief.state.unknown_cards
        assert node.belief.total_mass==1


def test_action_likelihood_updates_hidden_hand_not_just_card_ownership(cards):
    deck=Deck.create()
    a,b,c=(cards[f"coppe:{r}"] for r in (5,6,10))
    table=tuple(cards[f"denari:{r}"] for r in (1,2,3,4))
    own=(cards["spade:9"],)
    active=(a,b,c)+table+own
    state=GameState(player_hand=own,table_cards=table,opponent_hand_size=2,draw_pile_size=1,
                    current_player=Player.OPPONENT,
                    captured_cards=CapturedCards((),tuple(card for card in deck.cards if card not in active)))
    # Hands AB, AC, BC have prior 1/3. A and B have two captures; C has one.
    # P(a specific A action)=1/3*1/4 + 1/3*1/3 = 7/36.
    result=GameTree(SearchConfig(max_depth=1)).search(state)
    matches=[result.explored_states[i] for i in result.root.children if result.explored_states[i].move.played_card==a]
    assert len(matches)==2
    for node in matches:
        assert node.branch_probability==F(7,36)
        assert node.state.opponent_known_cards==()  # Hidden remaining card is not exposed.
        assert node.belief.probability(lambda w:b in w.opponent_hand)==F(3,7)
        assert node.belief.probability(lambda w:c in w.opponent_hand)==F(4,7)
    assert sum(result.explored_states[i].branch_probability for i in result.root.children)==1


def test_posterior_is_carried_to_later_moves_not_replaced_by_uniform_prior(cards):
    deck=Deck.create()
    a,b,c=(cards[f"coppe:{r}"] for r in (5,6,10))
    table=tuple(cards[f"denari:{r}"] for r in (1,2,3,4))
    own=(cards["spade:9"],cards["bastoni:9"])
    active=(a,b,c)+table+own
    state=GameState(player_hand=own,table_cards=table,opponent_hand_size=2,draw_pile_size=1,
                    current_player=Player.OPPONENT,
                    captured_cards=CapturedCards((),tuple(card for card in deck.cards if card not in active)))
    result=GameTree(SearchConfig(max_depth=2)).search(state)
    node=next(result.explored_states[i] for i in result.root.children if result.explored_states[i].move.played_card==a)
    for i in node.children:
        after_player=result.explored_states[i]
        assert after_player.belief.probability(lambda w:b in w.opponent_hand)==F(3,7)
        assert after_player.belief.probability(lambda w:c in w.opponent_hand)==F(4,7)


def test_bad_opponent_policy_is_rejected(final_two_turns):
    class InvalidPolicy:
        def probabilities(self,state,moves):
            return (F(2),)*len(moves)
    with pytest.raises(ValueError):
        GameTree(SearchConfig(max_depth=2),opponent=InvalidPolicy()).search(final_two_turns)


def test_injected_policy_can_assign_deterministic_weights(cards):
    class FirstAction:
        def probabilities(self,state,moves):
            return (F(1),)+(F(0),)*(len(moves)-1)
    state=GameState(player_hand=(cards["spade:9"],),opponent_hand_size=2,
                    opponent_known_cards=(cards["coppe:4"],cards["coppe:5"]),
                    table_cards=(cards["denari:2"],cards["denari:3"]),current_player=Player.OPPONENT)
    result=GameTree(SearchConfig(max_depth=1),opponent=FirstAction()).search(state)
    assert len(result.root.children)==1
    assert result.explored_states[1].move.played_card==cards["coppe:4"]
    assert result.explored_states[1].branch_probability==1
