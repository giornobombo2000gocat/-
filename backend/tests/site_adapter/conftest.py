import pytest
from engine.cards import Deck
from engine.game_state import CapturedCards, GameState, Player


def snapshot_for(state, *, status='active', snapshot_id='training-001'):
    ids=lambda cards: [card.id for card in cards]
    return dict(format_version='scopa-training-v1', mode='offline_training',variant='standard_scopa',
        snapshot_id=snapshot_id, game_status=status, player_hand=ids(state.player_hand),
        table_cards=ids(state.table_cards), known_played_cards=ids(state.played_cards),
        opponent_known_cards=ids(state.opponent_known_cards),
        captured_cards=dict(player=ids(state.captured_cards.player),opponent=ids(state.captured_cards.opponent)),
        score=dict(player=state.player_score,opponent=state.opponent_score),
        scopa_count=dict(player=state.scopa_count.player,opponent=state.scopa_count.opponent),
        current_player=state.current_player.value,turn_number=state.turn_number,round_number=state.round_number,
        opponent_hand_size=state.opponent_hand_size,draw_pile_size=state.draw_pile_size,
        last_capture_player=state.last_capture_player.value if state.last_capture_player else None,
        game_history=[dict(turn_number=h.turn_number,actor=h.actor.value,played_card=h.played_card.id,
            captured_cards=ids(h.captured_cards)) for h in state.game_history])


@pytest.fixture
def risk_state():
    deck=Deck.create(); cards={c.id:c for c in deck.cards}
    own=(cards['coppe:4'],cards['coppe:6']); table=(cards['denari:2'],cards['denari:3'])
    hidden=(cards['spade:9'],cards['bastoni:10'])
    return GameState(player_hand=own,table_cards=table,opponent_hand_size=1,
        captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in own+table+hidden),()),
        last_capture_player=Player.PLAYER)


@pytest.fixture
def risk_snapshot(risk_state):
    return snapshot_for(risk_state)
