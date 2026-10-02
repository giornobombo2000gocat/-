# Monte Carlo versus exact calculation

5000 iterations, seed 123, 2 worker processes. Same greedy player and uniform opponent policy for both methods.
Intervals below: approximate normal for EV, Wilson for probabilities; confidence 95%.

| Position | Metric | Exact | Monte Carlo | Absolute error | 95% interval |
| --- | --- | --- | --- | --- | --- |
| opponent-risk | expected_value | 467/168 (2.779762) | 2.771408 | 0.008354 | [2.747285, 2.795530] |
| opponent-risk | player_scopa | 0 (0.000000) | 0.000000 | 0.000000 | [0.000000, 0.000768] |
| opponent-risk | opponent_scopa | 1/2 (0.500000) | 0.504800 | 0.004800 | [0.490943, 0.518649] |
| future-scopa | expected_value | 631/160 (3.943750) | 3.957615 | 0.013865 | [3.943296, 3.971934] |
| future-scopa | player_scopa | 1/4 (0.250000) | 0.261800 | 0.011800 | [0.249801, 0.274165] |
| future-scopa | opponent_scopa | 0 (0.000000) | 0.000000 | 0.000000 | [0.000000, 0.000768] |

Manual probability checks:
- Opponent risk: hidden hand is either spade 9 or bastoni 10, equally likely. After discarding 4 onto 2+3, only 9 sweeps the table: probability 1/2.
- Future Scopa: opponent holds one of 5, 6, 2, 3, equally likely. After our discard 4, only its discard 5 lets our 9 sweep: probability 1/4.
- PASS: serial and parallel results agree exactly, including all estimates; changing chunk size has no mathematical effect.