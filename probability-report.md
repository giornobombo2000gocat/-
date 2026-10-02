# Probability calculations

Assumption: uniform hidden-card assignments, no behavioral inference.
Unknown pool A=denari:7, B=coppe:7, C=spade:2, D=bastoni:3.
36 other cards are captured and known. Opponent has 2 hidden cards; draw pile has 2.
Unordered world count = C(4,2) * C(2,2) = 6.

| Opponent hand | Draw pile | Exact probability |
| --- | --- | --- |
| bastoni:3, coppe:7 | denari:7, spade:2 | 1/6 |
| bastoni:3, denari:7 | coppe:7, spade:2 | 1/6 |
| bastoni:3, spade:2 | coppe:7, denari:7 | 1/6 |
| coppe:7, denari:7 | bastoni:3, spade:2 | 1/6 |
| coppe:7, spade:2 | bastoni:3, denari:7 | 1/6 |
| denari:7, spade:2 | bastoni:3, coppe:7 | 1/6 |

Early game: hand coppe 1,2,3; table denari 1,2,3,4; unknown N=33, four sevens, h=3, d=30.

| Event | Manual calculation | Expected | Actual | Match |
| --- | --- | --- | --- | --- |
| A in opponent hand | 3 favorable hands / 6 = 1/2 | 1/2 | 1/2 | PASS |
| Both sevens in opponent hand | 1 favorable hand / 6 = 1/6 (not 1/4) | 1/6 | 1/6 | PASS |
| No seven in opponent hand | C(2,0)C(2,2)/C(4,2) = 1/6 | 1/6 | 1/6 | PASS |
| Exactly one seven in opponent hand | C(2,1)C(2,1)/C(4,2) = 4/6 | 2/3 | 2/3 | PASS |
| At least one seven in opponent hand | 1 - 1/6 = 5/6 | 5/6 | 5/6 | PASS |
| A in hand and B in draw pile | 2 favorable worlds / 6 = 1/3 | 1/3 | 1/3 | PASS |
| B in hand given A in hand | 1 favorable remaining slot / 3 = 1/3 | 1/3 | 1/3 | PASS |
| B in draw pile given A in hand | 2 draw slots / 3 candidates = 2/3 | 2/3 | 2/3 | PASS |
| A belongs to draw pile of size 3 | 3 slots / 4 unknown cards = 3/4 | 3/4 | 3/4 | PASS |
| Next drawn card is A | Uniform next-card identity among 4 unknown cards = 1/4 | 1/4 | 1/4 | PASS |
| Early game: Sette Bello in opponent hand | 3 / 33 = 1/11 | 1/11 | 1/11 | PASS |
| Early game: at least one seven in opponent hand | 1 - C(29,3)/C(33,3) = 1 - 3654/5456 = 901/2728 | 901/2728 | 901/2728 | PASS |
| Early game: next drawn card is a seven | 4 / 33 | 4/33 | 4/33 | PASS |

Monte Carlo: samples=20000, seed=123, exact=False.
P(at least one seven): exact=5/6; empirical=333/400 (0.83250000); plug-in standard error=0.00264049.
Repeated input/config/seed produces an identical empirical distribution.

All 13 exact manual calculations matched. All 6 worlds have mass 1/6; total mass=1.