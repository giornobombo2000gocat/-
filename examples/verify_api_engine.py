"""Verify every route over real HTTP and compare analysis with direct engine calls."""
import argparse
import json
from fractions import Fraction
from pathlib import Path
from urllib.request import Request, urlopen

from engine.cards import Deck
from engine.decision_engine import DecisionConfig, DecisionEngine, save_analysis
from engine.game_state import CapturedCards, GameState, Player
from engine.game_tree import SearchConfig
from backend.app.schemas.games import GameStateSchema
from backend.app.services.serialization import state_from_schema, state_to_wire


def position():
    deck=Deck.create(); cards={c.id:c for c in deck.cards}
    own=(cards['coppe:4'],cards['coppe:6'])
    table=(cards['denari:2'],cards['denari:3'])
    hidden=(cards['spade:9'],cards['bastoni:10'])
    return GameState(player_hand=own,table_cards=table,opponent_hand_size=1,
        captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in own+table+hidden),()),
        last_capture_player=Player.PLAYER)


def fraction(data):
    return Fraction(data['numerator'],data['denominator'])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-url',default='http://127.0.0.1:8010')
    parser.add_argument('--output-dir',type=Path,default=Path('api-verification'))
    args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    transcript=[]
    def call(method,path,body=None,expected_status=200):
        request=Request(args.base_url+path,method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=60) as response:
            raw=response.read(); result=json.loads(raw)
            assert response.status==expected_status
            transcript.append(dict(method=method,path=path,status=response.status,request=body,response=result))
            if path.endswith('/analyze'):
                (args.output_dir/'analyze-response.raw.json').write_bytes(raw)
                (args.output_dir/'analyze-response.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(f'{method} {path}: {response.status}',flush=True)
            return result
    game=call('POST','/api/games',{},201); base=f"/api/games/{game['id']}"
    state=position(); payload=state_to_wire(state)
    (args.output_dir/'game-state.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    updated=call('POST',base+'/state',dict(state=payload,expected_revision=1))
    assert updated['revision']==2 and updated['state']==payload
    assert call('GET',base)==updated
    analysis=call('POST',base+'/analyze',dict(max_depth=2,probability_method='exact'))
    direct=DecisionEngine(DecisionConfig(search=SearchConfig(max_depth=2,probability_method='exact'))).analyze(state)
    save_analysis(direct,args.output_dir/'direct-engine-analysis.json')
    actual=analysis['recommended_move']; expected=direct.recommended_move
    # Compare raw engine objects independently of the response serialization code.
    assert actual['played_card']['id']==expected.played_card.id
    assert tuple(c['id'] for c in actual['captured_cards'])==tuple(c.id for c in expected.captured_cards)
    assert actual['creates_scopa']==expected.creates_scopa
    assert actual['capture_type']==expected.capture_type.value
    assert state_from_schema(GameStateSchema.model_validate(actual['resulting_state']))==expected.resulting_state
    assert fraction(analysis['expected_value'])==direct.expected_value
    assert len(analysis['all_moves'])==len(direct.all_moves)
    for api_move,engine_move in zip(analysis['all_moves'],direct.all_moves,strict=True):
        assert api_move['move']['played_card']['id']==engine_move.move.played_card.id
        assert tuple(c['id'] for c in api_move['move']['captured_cards'])==tuple(c.id for c in engine_move.move.captured_cards)
        for metric in ('expected_value','player_expected_value','opponent_expected_value',
                       'scopa_probability','opponent_scopa_probability','primiera_value','sette_bello_value'):
            assert fraction(api_move[metric])==getattr(engine_move,metric)
    assert call('GET',base+'/analysis')==analysis
    simulation=call('POST',base+'/simulate',dict(iterations=100,seed=123,max_depth=2,workers=2,
        move={'played_card':'coppe:6','captured_cards':[]}))
    assert simulation['iterations']==100 and simulation['state_revision']==2
    current=call('GET',base)
    assert current['state']==payload and current['has_analysis'] and current['has_simulation']
    (args.output_dir/'http-transcript.json').write_text(json.dumps(transcript,indent=2),encoding='utf-8')
    report=dict(game_id=game['id'],state_revision=2,base_url=args.base_url,all_six_endpoints_passed=True,
        recommended_move_matches=True,resulting_state_matches=True,all_move_metrics_match=True,
        api_played_card=actual['played_card']['id'],engine_played_card=expected.played_card.id,
        expected_value=str(direct.expected_value),legal_moves=len(direct.all_moves))
    (args.output_dir/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
