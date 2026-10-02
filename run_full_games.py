"""Reproducible full-round win rate benchmark (no external website)."""
import argparse
import csv
import json
import time
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from engine.simulation.full_game import play_batch
from engine.simulation.statistics import proportion_estimate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=10000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--output", type=Path, default=Path("full-game-results"))
    args = parser.parse_args()
    if args.games < 1 or args.workers < 1:
        parser.error("games and workers must be positive")
    started = time.perf_counter()
    batches = [tuple(range(i, min(i+50, args.games))) for i in range(0, args.games, 50)]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(play_batch, batch, args.seed) for batch in batches]
        for future in futures:
            results.extend(future.result())
            print(f"Completed {len(results)}/{args.games}", flush=True)
    counts = {key: sum(r.outcome == key for r in results) for key in ("win", "loss", "draw")}
    interval = proportion_estimate("wins", args.games, counts["win"], .95).confidence_interval
    report = dict(games=args.games, seed=args.seed, workers=args.workers,
                  game_definition="one complete 40-card round; all initial tables accepted",
                  software="DecisionEngine, depth=1, default evaluation weights; no private cards",
                  opponent="uniform random legal move", starters="alternating, player starts even indices",
                  **counts, win_rate=counts["win"]/args.games,
                  decisive_win_rate=counts["win"]/(counts["win"]+counts["loss"]) if counts["win"]+counts["loss"] else None,
                  win_rate_ci95=interval,
                  mean_player_points=sum(r.player_points for r in results)/args.games,
                  mean_opponent_points=sum(r.opponent_points for r in results)/args.games,
                  elapsed_seconds=time.perf_counter()-started)
    directory = args.output
    directory.mkdir(exist_ok=True)
    with (directory / "rounds.csv").open("w", newline="", encoding="utf-8") as file:
        rows = [dict(asdict(r), outcome=r.outcome) for r in results]
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (directory / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
