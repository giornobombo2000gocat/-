"""Exercise all six endpoints through a running HTTP server using stdlib only."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--output',type=Path,default=Path('api-demo-results.json'))
    args=parser.parse_args(); transcript=[]
    def call(method,path,body=None):
        data=json.dumps(body).encode() if body is not None else None
        request=Request(args.base_url+path,data=data,method=method,headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=60) as response:
            result=json.loads(response.read())
            transcript.append(dict(method=method,path=path,request=body,status=response.status,response=result))
            print(f'{method} {path}: {response.status}',flush=True)
            return result
    game=call('POST','/api/games',{})
    base=f"/api/games/{game['id']}"
    updated=call('POST',base+'/state',{'expected_revision':1,'state':{
        'player_hand':['coppe:8'],'table_cards':['denari:1','denari:2','denari:3','denari:5','denari:7'],
        'opponent_hand_size':1}})
    assert updated['revision']==2
    assert call('GET',base)==updated
    analysis=call('POST',base+'/analyze',{'max_depth':1})
    assert len(analysis['all_moves'])==3
    assert call('GET',base+'/analysis')==analysis
    result=call('POST',base+'/simulate',{'iterations':100,'seed':123,'max_depth':2,'workers':2})
    assert result['iterations']==100 and result['state_revision']==2
    args.output.write_text(json.dumps(transcript,indent=2),encoding='utf-8')
    print('PASS: all six endpoints exercised over HTTP')


if __name__=='__main__':
    main()
