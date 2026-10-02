"""Offline training example; no Betsson connection or website actions."""
import argparse
import json
from fractions import Fraction
from pathlib import Path

from engine.decision_engine import DecisionEngine, save_analysis
from site_adapter.betsson import MockBetssonAdapter


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixture',type=Path,default=Path('site_adapter/betsson/fixtures/risk-training.json'))
    parser.add_argument('--output-dir',type=Path,default=Path('adapter-verification'))
    args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    payload=json.loads(args.fixture.read_text(encoding='utf-8'))
    adapter=MockBetssonAdapter([payload]); result=adapter.analyze()
    direct=DecisionEngine().analyze(result.game_state)
    assert result.analysis==direct
    assert result.analysis==adapter.analyze().analysis
    assert result.expected_value==Fraction(1115,336)
    save_analysis(result.analysis,args.output_dir/'mock-analysis.json',include_timing=True)
    report=dict(mode=payload['mode'],format_version=payload['format_version'],
        snapshot_id=result.observation.snapshot_id,source_status=result.observation.game_status.value,
        status=result.status,legal_moves=len(result.legal_moves),
        recommended_card=result.recommended_move.played_card.id,
        expected_value=str(result.expected_value),scopa_probability=str(result.scopa_probability),
        primiera_value=str(result.primiera_value),sette_bello_value=str(result.sette_bello_value),
        calculation_time_seconds=result.calculation_time,matches_direct_engine=True,
        site_connected=False,actions_on_site=0)
    (args.output_dir/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
