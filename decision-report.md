# Decision Engine verified examples

EV = expected player utility minus expected opponent utility.
Cutoff utility is explicitly heuristic; opponent policy is uniform over legal actions per possible hand.

## sette

Hand: ['coppe:8']; table: ['denari:7', 'coppe:1', 'spade:2', 'bastoni:3', 'spade:5']
Depth: 1; explored nodes: 4; method: exact

| Play | Capture | Immediate evaluation | Expected value | Player utility | Opponent utility | P(player Scopa) | P(opponent Scopa) | Primiera strength | Sette Bello points | Recommended |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| coppe:8 | bastoni:3, spade:5 | 443/840 | 443/840 | 443/840 | 0 | 0 | 0 | 38 | 0 |  |
| coppe:8 | coppe:1, denari:7 | 1357/840 | 1357/840 | 1357/840 | 0 | 0 | 0 | 37 | 1 | YES |
| coppe:8 | coppe:1, spade:2, spade:5 | 197/420 | 197/420 | 197/420 | 0 | 0 | 0 | 31 | 0 |  |

## risk-depth1

Hand: ['coppe:4', 'coppe:6']; table: ['denari:2', 'denari:3']
Depth: 1; explored nodes: 3; method: exact

| Play | Capture | Immediate evaluation | Expected value | Player utility | Opponent utility | P(player Scopa) | P(opponent Scopa) | Primiera strength | Sette Bello points | Recommended |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| coppe:4 | discard | 73/20 | 73/20 | 73/20 | 0 | 0 | 0 | 84 | 1 | YES |
| coppe:6 | discard | 73/20 | 73/20 | 73/20 | 0 | 0 | 0 | 84 | 1 |  |

## risk-depth2

Hand: ['coppe:4', 'coppe:6']; table: ['denari:2', 'denari:3']
Depth: 2; explored nodes: 7; method: exact

| Play | Capture | Immediate evaluation | Expected value | Player utility | Opponent utility | P(player Scopa) | P(opponent Scopa) | Primiera strength | Sette Bello points | Recommended |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| coppe:4 | discard | 73/20 | 467/168 | 73/20 | 731/840 | 0 | 1/2 | 84 | 1 |  |
| coppe:6 | discard | 73/20 | 1115/336 | 73/20 | 557/1680 | 0 | 0 | 84 | 1 | YES |

PASS: all legal moves compared; shorter Sette Bello capture preferred; lookahead changes recommendation to avoid opponent Scopa.
Repeated input/config produces identical mathematical results and JSON. Timing is deliberately omitted from the deterministic reports.