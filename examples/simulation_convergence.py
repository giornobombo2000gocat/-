"""Ten fixed positions; actual independent rollouts at three sample budgets."""
import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from time import perf_counter

from engine.cards import Deck
from engine.game_state import CapturedCards, GameState, Player
from engine.rules import RulesEngine
from engine.simulation import SimulationConfig, SimulationEngine, save_simulation


@dataclass(frozen=True)
class Case:
    name: str
    state: GameState
    played_id: str
    depth: int

    @property
    def move(self):
        return next(m for m in RulesEngine().get_legal_moves(self.state) if m.played_card.id==self.played_id)


def cases():
    deck=Deck.create(); cards={c.id:c for c in deck.cards}
    # own hand, table, unknown pool, forced play, depth, opponent size, draw size
    specifications=[
        ('risk-9',('coppe:4','coppe:6'),('denari:2','denari:3'),('spade:9','bastoni:10'),'coppe:4',2,1,0),
        ('avoid-9',('coppe:4','coppe:6'),('denari:2','denari:3'),('spade:9','bastoni:10'),'coppe:6',2,1,0),
        ('capture-5',('coppe:5','coppe:8'),('denari:2','spade:3'),('denari:7','bastoni:8','spade:10'),'coppe:5',2,1,0),
        ('sette-capture',('coppe:8','coppe:4'),('denari:7','spade:1'),('bastoni:2','spade:4','denari:10'),'coppe:8',2,1,0),
        ('single-priority',('coppe:7','coppe:9'),('denari:7','spade:2','bastoni:5'),('denari:2','spade:5','bastoni:9'),'coppe:7',2,1,0),
        ('three-captures',('coppe:8','coppe:10'),('denari:1','spade:2','bastoni:3','denari:5','spade:7'),('bastoni:8','denari:9','spade:10'),'coppe:8',2,1,0),
        ('two-card-opponent',('coppe:4','coppe:8'),('denari:2','spade:3'),('denari:7','bastoni:9','spade:10','bastoni:5'),'coppe:4',2,2,0),
        ('future-scopa',('coppe:4','coppe:9'),(),('denari:5','spade:6','bastoni:2','denari:3'),'coppe:4',3,1,2),
        ('future-sette',('coppe:3','coppe:7'),('spade:1',),('denari:7','bastoni:4','spade:6','denari:2'),'coppe:3',3,1,2),
        ('new-deal',('coppe:4',),('denari:2',),('spade:6','denari:7','bastoni:8'),'coppe:4',3,1,2),
    ]
    result=[]
    for index,(name,own,table,pool,play,depth,opponent,draw) in enumerate(specifications):
        own=tuple(cards[k] for k in own); table=tuple(cards[k] for k in table)
        pool=tuple(cards[k] for k in pool)
        rest=tuple(c for c in deck.cards if c not in own+table+pool)
        # Different publicly known capture standings, explicitly stored in manifest.
        captured=CapturedCards(rest,()) if index in (0,7) else CapturedCards(rest[::2],rest[1::2])
        state=GameState(player_hand=own,table_cards=table,opponent_hand_size=opponent,draw_pile_size=draw,
            captured_cards=captured,last_capture_player=Player.PLAYER)
        result.append(Case(name,state,play,depth))
    return tuple(result)


def manifest(case):
    state=case.state
    return dict(name=case.name,player_hand=[c.id for c in state.player_hand],table=[c.id for c in state.table_cards],
        unknown=[c.id for c in state.unknown_cards],opponent_hand_size=state.opponent_hand_size,
        draw_pile_size=state.draw_pile_size,captured_player=[c.id for c in state.captured_cards.player],
        captured_opponent=[c.id for c in state.captured_cards.opponent],last_capture_player=state.last_capture_player,
        played=case.played_id,capture=[c.id for c in case.move.captured_cards],depth=case.depth)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output-dir',type=Path,default=Path('convergence'))
    parser.add_argument('--resume',action='store_true',help='Reuse completed rows only when exact value and position manifest agree')
    args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    all_cases=cases(); start=perf_counter()
    previous_manifest=json.loads((args.output_dir/'positions.json').read_text(encoding='utf-8')) if args.resume and (args.output_dir/'positions.json').exists() else []
    previous_rows=json.loads((args.output_dir/'results.json').read_text(encoding='utf-8')) if args.resume and (args.output_dir/'results.json').exists() else []
    (args.output_dir/'positions.json').write_text(json.dumps([manifest(c) for c in all_cases],indent=2),encoding='utf-8')
    rows=[]; errors={n:[] for n in (1000,10000,100000)}
    for index,case in enumerate(all_cases,1):
        config=SimulationConfig(seed=123,max_depth=case.depth,workers=args.workers,chunk_size=1024)
        exact=SimulationEngine(config).exact_reference(case.state,case.move)
        value=dict(exact.metrics)['expected_value']
        if args.resume and index<=len(previous_rows) and index<=len(previous_manifest):
            saved=previous_rows[index-1]
            if previous_manifest[index-1]==manifest(case) and saved['exact']==str(value) and set(saved['runs'])=={'1000','10000','100000'}:
                rows.append(saved)
                for n in errors:
                    errors[n].append(Fraction(saved['runs'][str(n)]['error_fraction']))
                print(f'{index}/10 {case.name}: retained completed measured runs',flush=True)
                continue
        print(f'{index}/10 {case.name}: exact EV={value}, nodes={exact.explored_nodes}',flush=True)
        row=dict(position=index,name=case.name,exact=str(value),exact_decimal=float(value),nodes=exact.explored_nodes,runs={})
        for n in (1000,10000,100000):
            result=SimulationEngine(SimulationConfig(iterations=n,seed=123,max_depth=case.depth,
                workers=args.workers,chunk_size=1024)).simulate(case.state,case.move)
            save_simulation(result,args.output_dir/f'{index:02d}-{n}.json')
            error=abs(result.expected_value.mean-value); errors[n].append(error)
            row['runs'][str(n)]=dict(mean=float(result.expected_value.mean),mean_fraction=str(result.expected_value.mean),
                error=float(error),error_fraction=str(error),standard_error=result.expected_value.standard_error,
                confidence_interval=result.expected_value.confidence_interval,seconds=result.calculation_time)
            print(f'  n={n}: EV={float(result.expected_value.mean):.9f}, error={float(error):.9f}, seconds={result.calculation_time:.2f}',flush=True)
        rows.append(row)
        (args.output_dir/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    lines=['# Ten-state Monte Carlo convergence benchmark','',
        'Metric: expected player utility minus expected opponent utility (EV). Absolute error = |MC - Exact|.',
        'Seed 123 for every run. Same forced initial move, greedy public-information player policy and uniform opponent policy in both methods.',
        'Budgets share the same sample prefix; all three budgets execute actual rollouts separately. Depth cutoff uses heuristic utility.', '',
        '| # | Position | Exact | MC 1k | MC 10k | MC 100k | Error 1k | Error 10k | Error 100k | Monotone decrease |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    monotone=0; improved=0
    for row in rows:
        r=[row['runs'][str(n)] for n in (1000,10000,100000)]
        decreasing=r[0]['error']>=r[1]['error']>=r[2]['error']; monotone+=decreasing
        improved+=r[2]['error']<r[0]['error']
        lines.append(f"| {row['position']} | {row['name']} | {row['exact_decimal']:.9f} | "+
            ' | '.join(f"{item['mean']:.9f}" for item in r)+' | '+
            ' | '.join(f"{item['error']:.9f}" for item in r)+f" | {'yes' if decreasing else 'no'} |")
    lines+=['','| Budget | Mean absolute error | Root mean squared error |', '| --- | --- | --- |']
    for n,values in errors.items():
        mae=sum(values,Fraction())/len(values)
        rmse=(float(sum((v*v for v in values),Fraction())/len(values)))**.5
        lines.append(f'| {n} | {float(mae):.9f} | {rmse:.9f} |')
    lines+=['',f'100k error smaller than 1k: {improved}/10. Monotone across all three budgets: {monotone}/10.',
        'Individual realized errors need not decrease monotonically. For independent bounded rollouts, the standard deviation of the sample mean scales as 1/sqrt(N); this is a statistical rate, not a guarantee for each sample prefix.',
        f'Sum of recorded simulation runtimes: {sum(run["seconds"] for row in rows for run in row["runs"].values()):.2f} seconds.',
        f'Final invocation wall runtime (may reuse completed rows): {perf_counter()-start:.2f} seconds.', '',
        'positions.json contains complete capture piles and active card IDs; results.json retains exact fractions, per-run errors, standard errors, confidence intervals and timings.']
    report='\n'.join(lines)
    (args.output_dir/'report.md').write_text(report,encoding='utf-8')
    print(report,flush=True)


if __name__=='__main__':
    main()
