"""Small exact references compared with reproducible parallel Monte Carlo."""
from pathlib import Path
from dataclasses import replace
from engine.cards import Deck
from engine.game_state import CapturedCards, GameState, Player
from engine.rules import RulesEngine
from engine.simulation import SimulationConfig, SimulationEngine, save_simulation


def main():
    deck=Deck.create(); cards={c.id:c for c in deck.cards}
    lines=['# Monte Carlo versus exact calculation','',
           '5000 iterations, seed 123, 2 worker processes. Same greedy player and uniform opponent policy for both methods.',
           'Intervals below: approximate normal for EV, Wilson for probabilities; confidence 95%.', '',
           '| Position | Metric | Exact | Monte Carlo | Absolute error | 95% interval |',
           '| --- | --- | --- | --- | --- | --- |']
    for future in (False,True):
        own=tuple(cards[k] for k in (('coppe:4','coppe:9') if future else ('coppe:4','coppe:6')))
        table=() if future else (cards['denari:2'],cards['denari:3'])
        pool=tuple(cards[k] for k in (('denari:5','spade:6','bastoni:2','denari:3') if future else ('spade:9','bastoni:10')))
        active=own+table+pool
        state=GameState(player_hand=own,table_cards=table,opponent_hand_size=1,draw_pile_size=2 if future else 0,
            captured_cards=CapturedCards(tuple(c for c in deck.cards if c not in active),()),last_capture_player=Player.PLAYER)
        move=next(m for m in RulesEngine().get_legal_moves(state) if m.played_card.rank==4)
        cfg=SimulationConfig(iterations=5000,seed=123,workers=2,max_depth=3 if future else 2)
        result=SimulationEngine(cfg).compare_exact(state,move)
        assert result.simulation==SimulationEngine(replace(cfg,workers=1,chunk_size=79)).simulate(state,move)
        name='future-scopa' if future else 'opponent-risk'
        save_simulation(result,Path(f'simulation-{name}.json'))
        for item in result.comparisons:
            if item.name in ('expected_value','player_scopa','opponent_scopa'):
                low,high=item.confidence_interval
                lines.append(f'| {name} | {item.name} | {item.exact} ({float(item.exact):.6f}) | {float(item.monte_carlo):.6f} | {float(item.absolute_error):.6f} | [{low:.6f}, {high:.6f}] |')
    lines += ['', 'Manual probability checks:',
              '- Opponent risk: hidden hand is either spade 9 or bastoni 10, equally likely. After discarding 4 onto 2+3, only 9 sweeps the table: probability 1/2.',
              '- Future Scopa: opponent holds one of 5, 6, 2, 3, equally likely. After our discard 4, only its discard 5 lets our 9 sweep: probability 1/4.',
              '- PASS: serial and parallel results agree exactly, including all estimates; changing chunk size has no mathematical effect.']
    report='\n'.join(lines)
    Path('simulation-report.md').write_text(report,encoding='utf-8')
    print(report)


if __name__=='__main__':
    main()
