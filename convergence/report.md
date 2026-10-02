# Ten-state Monte Carlo convergence benchmark

Metric: expected player utility minus expected opponent utility (EV). Absolute error = |MC - Exact|.
Seed 123 for every run. Same forced initial move, greedy public-information player policy and uniform opponent policy in both methods.
Budgets share the same sample prefix; all three budgets execute actual rollouts separately. Depth cutoff uses heuristic utility.

| # | Position | Exact | MC 1k | MC 10k | MC 100k | Error 1k | Error 10k | Error 100k | Monotone decrease |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | risk-9 | 2.779761905 | 2.784983333 | 2.769145000 | 2.783312476 | 0.005221429 | 0.010616905 | 0.003550571 | no |
| 2 | avoid-9 | 1.001785714 | 1.002417857 | 1.000500357 | 1.002215571 | 0.000632143 | 0.001285357 | 0.000429857 | no |
| 3 | capture-5 | 1.200000000 | 1.200000000 | 1.200000000 | 1.200000000 | 0.000000000 | 0.000000000 | 0.000000000 | yes |
| 4 | sette-capture | 2.200000000 | 2.200000000 | 2.200000000 | 2.200000000 | 0.000000000 | 0.000000000 | 0.000000000 | yes |
| 5 | single-priority | 1.190476190 | 1.191942857 | 1.189717857 | 1.190721857 | 0.001466667 | 0.000758333 | 0.000245667 | yes |
| 6 | three-captures | 0.651190476 | 0.621807143 | 0.645074643 | 0.648221393 | 0.029383333 | 0.006115833 | 0.002969083 | yes |
| 7 | two-card-opponent | -0.726785714 | -0.718375000 | -0.723818214 | -0.726384036 | 0.008410714 | 0.002967500 | 0.000401679 | yes |
| 8 | future-scopa | 3.943750000 | 3.929650000 | 3.949860000 | 3.942504500 | 0.014100000 | 0.006110000 | 0.001245500 | yes |
| 9 | future-sette | 0.193452381 | 0.168922619 | 0.209359524 | 0.191397024 | 0.024529762 | 0.015907143 | 0.002055357 | yes |
| 10 | new-deal | -0.221031746 | -0.261580952 | -0.228855476 | -0.224566131 | 0.040549206 | 0.007823730 | 0.003534385 | yes |

| Budget | Mean absolute error | Root mean squared error |
| --- | --- | --- |
| 1000 | 0.012429325 | 0.018462643 |
| 10000 | 0.005158480 | 0.007160554 |
| 100000 | 0.001443210 | 0.002002402 |

100k error smaller than 1k: 8/10. Monotone across all three budgets: 8/10.
Individual realized errors need not decrease monotonically. For independent bounded rollouts, the standard deviation of the sample mean scales as 1/sqrt(N); this is a statistical rate, not a guarantee for each sample prefix.
Sum of recorded simulation runtimes: 635.69 seconds.
Final invocation wall runtime (may reuse completed rows): 0.22 seconds.

positions.json contains complete capture piles and active card IDs; results.json retains exact fractions, per-run errors, standard errors, confidence intervals and timings.