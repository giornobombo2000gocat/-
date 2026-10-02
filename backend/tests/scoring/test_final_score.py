import pytest
from engine.cards import Card, Deck, DeckConfig
from engine.game_state import GameState, CapturedCards, PlayerCounts, Player
from engine.moves import Move
from engine.rules import RulesEngine
from engine.scoring import ScoringConfig, ScoringEngine, IncompleteRound


def settled(deck):
    return GameState(deck=deck, captured_cards=CapturedCards(tuple(c for c in deck.cards if c.rank <= 7),
                                                          tuple(c for c in deck.cards if c.rank > 7)),
                     scopa_count=PlayerCounts(2,1), player_score=4, opponent_score=8)


def test_final_known_complete_round_and_cumulative_score(deck):
    state = settled(deck)
    result = ScoringEngine().calculate_score(state)
    assert result.breakdown.captured_cards.player_value == 28
    assert result.breakdown.denari.player_value == 7
    assert result.breakdown.sette_bello.points == PlayerCounts(1,0)
    assert result.breakdown.primiera.player.value == 84
    assert result.breakdown.primiera.opponent.value == 40
    assert result.round_points == PlayerCounts(6,1)
    assert result.previous_scores == PlayerCounts(4,8)
    assert result.total_scores == PlayerCounts(10,9)


def test_final_card_and_denari_ties(deck):
    ranks = {1,2,3,6,8}
    state = GameState(captured_cards=CapturedCards(tuple(c for c in deck.cards if c.rank in ranks),
                                                 tuple(c for c in deck.cards if c.rank not in ranks)))
    result = ScoringEngine().calculate_score(state)
    assert result.breakdown.captured_cards.points == PlayerCounts()
    assert result.breakdown.denari.points == PlayerCounts()
    assert result.round_points == PlayerCounts(0,2)


def test_final_missing_suits_no_primiera_for_either_side(deck):
    state = GameState(captured_cards=CapturedCards(tuple(c for c in deck.cards if c.suit != "bastoni"),
                                                 tuple(c for c in deck.cards if c.suit == "bastoni")))
    assert ScoringEngine().calculate_score(state).round_points == PlayerCounts(3,0)


def test_scoring_is_pure_and_repeatable(deck):
    state = settled(deck)
    engine = ScoringEngine()
    assert engine.calculate_score(state) == engine.calculate_score(state)
    assert state.player_score == 4 and state.scopa_count == PlayerCounts(2,1)


def test_final_rejects_partial_round():
    with pytest.raises(IncompleteRound):
        ScoringEngine().calculate_score(GameState())


@pytest.mark.parametrize("zone", ["player_hand", "opponent_known_cards", "table_cards"])
def test_final_rejects_unsettled_zones(deck, zone):
    remaining = deck.cards[0]
    kwargs = {zone: (remaining,)}
    if zone == "opponent_known_cards":
        kwargs["opponent_hand_size"] = 1
    state = GameState(captured_cards=CapturedCards(deck.cards[1:], ()), **kwargs)
    with pytest.raises(IncompleteRound):
        ScoringEngine().calculate_score(state)


@pytest.mark.parametrize("counts", [{"draw_pile_size":1}, {"opponent_hand_size":1}])
def test_final_rejects_hidden_remaining_cards(deck, counts):
    state = GameState(captured_cards=CapturedCards(deck.cards[1:], ()), **counts)
    with pytest.raises(IncompleteRound):
        ScoringEngine().calculate_score(state)


def test_partial_evaluation_is_available_without_final_claim(cards):
    result = ScoringEngine().evaluate_captures(CapturedCards((cards["denari:7"],), ()), PlayerCounts(1,0))
    assert result.round_points == PlayerCounts(4,0)
    assert not result.primiera.player.eligible


def test_custom_deck_and_scoring_config():
    config = ScoringConfig(deck_config=DeckConfig(("gold", "blue"), (1,2), (3,5)),
                           denari_suit="gold", sette_bello_rank=2, primiera_values=((1,10),(2,20)))
    deck = Deck.create(config.deck_config)
    state = GameState(deck=deck, captured_cards=CapturedCards(deck.cards, ()))
    assert ScoringEngine(config).calculate_score(state).round_points == PlayerCounts(4,0)


def test_configuration_deck_mismatch_rejected(deck):
    state = settled(deck)
    config = ScoringConfig(deck_config=DeckConfig(values=tuple(range(2,12))))
    with pytest.raises(ValueError):
        ScoringEngine(config).calculate_score(state)


def test_foreign_capture_is_not_silently_scored():
    with pytest.raises(ValueError):
        ScoringEngine().evaluate_captures(CapturedCards((Card("x", "alien", 1,1),),()), PlayerCounts())


def test_rules_final_transition_integrates_with_scoring(deck, cards):
    active = {cards["coppe:5"], cards["denari:2"], cards["denari:3"]}
    state = GameState(player_hand=(cards["coppe:5"],), table_cards=(cards["denari:2"],cards["denari:3"]),
                      captured_cards=CapturedCards((), tuple(c for c in deck.cards if c not in active)))
    after = RulesEngine().apply_move(state, Move(state.player_hand[0],state.table_cards))
    result = ScoringEngine().calculate_score(after)
    assert after.scopa_count == PlayerCounts()  # No last-play Scopa to double count.
    assert result.round_points == PlayerCounts(0,4)


@pytest.mark.parametrize("kwargs", [
    {"scopa_points":-1}, {"denari_points":True}, {"denari_suit":"missing"},
    {"sette_bello_rank":11}, {"primiera_values":((1,16),)},
    {"primiera_values":((1,16),)*10}, {"primiera_values":((1,-2),)},
])
def test_invalid_scoring_configuration(kwargs):
    with pytest.raises(ValueError):
        ScoringConfig(**kwargs)
