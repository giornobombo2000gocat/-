"""Nested offline benchmarks for three independent players."""
import csv
import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from engine.simulation.multiplayer import play_batch
from engine.simulation.statistics import proportion_estimate


def main(players=3):
    seed, workers = 20261001, 4
    started = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(play_batch, tuple(range(i, i+50)), seed, players) for i in range(0, 10000, 50)]
        for future in futures:
            results.extend(future.result())
            if len(results) % 500 == 0:
                print(f"Completed {len(results)}/10000", flush=True)
    elapsed = time.perf_counter() - started
    directory = Path("three-player-results" if players == 3 else "four-player-results")
    directory.mkdir(exist_ok=True)
    reports = []
    for n in (100, 200, 500, 1000, 10000):
        subset = results[:n]
        counts = {key: sum(r.outcome == key for r in subset) for key in ("win", "loss", "draw")}
        report = dict(games=n, seed=seed, players=players, software="multiplayer depth-one public heuristic; own utility minus strongest rival",
                      opponents=f"{players-1} independent uniform legal-move policies; no team", definition="one complete 40-card round; unique first place is win; shared first is draw; any lower place is loss",
                      nested_sample=True, **counts, win_rate=counts["win"]/n,
                      win_rate_ci95=proportion_estimate("wins", n, counts["win"], .95).confidence_interval,
                      mean_points=[sum(r.points[i] for r in subset)/n for i in range(players)],
                      starter_counts=[sum(r.starter == i for r in subset) for i in range(players)])
        reports.append(report)
        (directory/f"summary-{n}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        rows = [dict(asdict(r), outcome=r.outcome) for r in subset]
        with (directory/f"rounds-{n}.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    combined = dict(elapsed_seconds=elapsed, workers=workers, reports=reports)
    (directory/"summary.json").write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(json.dumps(combined, indent=2), flush=True)


if __name__ == "__main__":
    main()
