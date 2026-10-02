# Fixed scoring positions

All pairs are (player, opponent). Every position assigns all 40 cards.

## P1

Player owns ranks 1-7 in every suit; opponent owns 8-10.

Cards captured: (28, 12); points: (1, 0)  
Scopa: (2, 1); points: (2, 1)  
Denari: (7, 3); points: (1, 0)  
Sette Bello: (1, 0); points: (1, 0)  
Primiera: (84, 40); points: (1, 0)  
Primiera eligible: (True, True); missing suits: ((), ())  
Previous score: (4, 8)  
Final score: round=(6, 1); total=(10, 9)

Expected: `ExpectedScore(cards=(28, 12), cards_points=(1, 0), scopa=(2, 1), scopa_points=(2, 1), denari=(7, 3), denari_points=(1, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(84, 40), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(1, 0), round_score=(6, 1), total_score=(10, 9))`

Actual: `ExpectedScore(cards=(28, 12), cards_points=(1, 0), scopa=(2, 1), scopa_points=(2, 1), denari=(7, 3), denari_points=(1, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(84, 40), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(1, 0), round_score=(6, 1), total_score=(10, 9))`

**MATCH**

## P2

Player owns ranks 8-10 in every suit; opponent owns 1-7.

Cards captured: (12, 28); points: (0, 1)  
Scopa: (1, 2); points: (1, 2)  
Denari: (3, 7); points: (0, 1)  
Sette Bello: (0, 1); points: (0, 1)  
Primiera: (40, 84); points: (0, 1)  
Primiera eligible: (True, True); missing suits: ((), ())  
Previous score: (8, 4)  
Final score: round=(1, 6); total=(9, 10)

Expected: `ExpectedScore(cards=(12, 28), cards_points=(0, 1), scopa=(1, 2), scopa_points=(1, 2), denari=(3, 7), denari_points=(0, 1), sette_bello=(0, 1), sette_bello_points=(0, 1), primiera=(40, 84), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(0, 1), round_score=(1, 6), total_score=(9, 10))`

Actual: `ExpectedScore(cards=(12, 28), cards_points=(0, 1), scopa=(1, 2), scopa_points=(1, 2), denari=(3, 7), denari_points=(0, 1), sette_bello=(0, 1), sette_bello_points=(0, 1), primiera=(40, 84), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(0, 1), round_score=(1, 6), total_score=(9, 10))`

**MATCH**

## P3

Player owns ranks 1,2,3,6,8 in every suit; opponent owns the rest.

Cards captured: (20, 20); points: (0, 0)  
Scopa: (0, 0); points: (0, 0)  
Denari: (5, 5); points: (0, 0)  
Sette Bello: (0, 1); points: (0, 1)  
Primiera: (72, 84); points: (0, 1)  
Primiera eligible: (True, True); missing suits: ((), ())  
Previous score: (0, 0)  
Final score: round=(0, 2); total=(0, 2)

Expected: `ExpectedScore(cards=(20, 20), cards_points=(0, 0), scopa=(0, 0), scopa_points=(0, 0), denari=(5, 5), denari_points=(0, 0), sette_bello=(0, 1), sette_bello_points=(0, 1), primiera=(72, 84), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(0, 1), round_score=(0, 2), total_score=(0, 2))`

Actual: `ExpectedScore(cards=(20, 20), cards_points=(0, 0), scopa=(0, 0), scopa_points=(0, 0), denari=(5, 5), denari_points=(0, 0), sette_bello=(0, 1), sette_bello_points=(0, 1), primiera=(72, 84), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(0, 1), round_score=(0, 2), total_score=(0, 2))`

**MATCH**

## P4

Player owns odd ranks in every suit; opponent owns even ranks.

Cards captured: (20, 20); points: (0, 0)  
Scopa: (1, 1); points: (1, 1)  
Denari: (5, 5); points: (0, 0)  
Sette Bello: (1, 0); points: (1, 0)  
Primiera: (84, 72); points: (1, 0)  
Primiera eligible: (True, True); missing suits: ((), ())  
Previous score: (0, 0)  
Final score: round=(3, 1); total=(3, 1)

Expected: `ExpectedScore(cards=(20, 20), cards_points=(0, 0), scopa=(1, 1), scopa_points=(1, 1), denari=(5, 5), denari_points=(0, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(84, 72), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(1, 0), round_score=(3, 1), total_score=(3, 1))`

Actual: `ExpectedScore(cards=(20, 20), cards_points=(0, 0), scopa=(1, 1), scopa_points=(1, 1), denari=(5, 5), denari_points=(0, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(84, 72), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(1, 0), round_score=(3, 1), total_score=(3, 1))`

**MATCH**

## P5

Player owns denari, coppe and spade; opponent owns all bastoni.

Cards captured: (30, 10); points: (1, 0)  
Scopa: (0, 0); points: (0, 0)  
Denari: (10, 0); points: (1, 0)  
Sette Bello: (1, 0); points: (1, 0)  
Primiera: (63, 21); points: (0, 0)  
Primiera eligible: (False, False); missing suits: (('bastoni',), ('denari', 'coppe', 'spade'))  
Previous score: (0, 0)  
Final score: round=(3, 0); total=(3, 0)

Expected: `ExpectedScore(cards=(30, 10), cards_points=(1, 0), scopa=(0, 0), scopa_points=(0, 0), denari=(10, 0), denari_points=(1, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(63, 21), primiera_eligible=(False, False), primiera_missing=(('bastoni',), ('denari', 'coppe', 'spade')), primiera_points=(0, 0), round_score=(3, 0), total_score=(3, 0))`

Actual: `ExpectedScore(cards=(30, 10), cards_points=(1, 0), scopa=(0, 0), scopa_points=(0, 0), denari=(10, 0), denari_points=(1, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(63, 21), primiera_eligible=(False, False), primiera_missing=(('bastoni',), ('denari', 'coppe', 'spade')), primiera_points=(0, 0), round_score=(3, 0), total_score=(3, 0))`

**MATCH**

## P6

Player owns all bastoni and rank 8 of each other suit; opponent owns the rest.

Cards captured: (13, 27); points: (0, 1)  
Scopa: (1, 0); points: (1, 0)  
Denari: (1, 9); points: (0, 1)  
Sette Bello: (0, 1); points: (0, 1)  
Primiera: (51, 63); points: (1, 0)  
Primiera eligible: (True, False); missing suits: ((), ('bastoni',))  
Previous score: (0, 0)  
Final score: round=(2, 3); total=(2, 3)

Expected: `ExpectedScore(cards=(13, 27), cards_points=(0, 1), scopa=(1, 0), scopa_points=(1, 0), denari=(1, 9), denari_points=(0, 1), sette_bello=(0, 1), sette_bello_points=(0, 1), primiera=(51, 63), primiera_eligible=(True, False), primiera_missing=((), ('bastoni',)), primiera_points=(1, 0), round_score=(2, 3), total_score=(2, 3))`

Actual: `ExpectedScore(cards=(13, 27), cards_points=(0, 1), scopa=(1, 0), scopa_points=(1, 0), denari=(1, 9), denari_points=(0, 1), sette_bello=(0, 1), sette_bello_points=(0, 1), primiera=(51, 63), primiera_eligible=(True, False), primiera_missing=((), ('bastoni',)), primiera_points=(1, 0), round_score=(2, 3), total_score=(2, 3))`

**MATCH**

## P7

Player owns 1,2,3,4,7 in denari/coppe and 1,2,3,4,6 in spade/bastoni; opponent owns the rest.

Cards captured: (20, 20); points: (0, 0)  
Scopa: (1, 2); points: (1, 2)  
Denari: (5, 5); points: (0, 0)  
Sette Bello: (1, 0); points: (1, 0)  
Primiera: (78, 78); points: (0, 0)  
Primiera eligible: (True, True); missing suits: ((), ())  
Previous score: (0, 0)  
Final score: round=(2, 2); total=(2, 2)

Expected: `ExpectedScore(cards=(20, 20), cards_points=(0, 0), scopa=(1, 2), scopa_points=(1, 2), denari=(5, 5), denari_points=(0, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(78, 78), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(0, 0), round_score=(2, 2), total_score=(2, 2))`

Actual: `ExpectedScore(cards=(20, 20), cards_points=(0, 0), scopa=(1, 2), scopa_points=(1, 2), denari=(5, 5), denari_points=(0, 0), sette_bello=(1, 0), sette_bello_points=(1, 0), primiera=(78, 78), primiera_eligible=(True, True), primiera_missing=((), ()), primiera_points=(0, 0), round_score=(2, 2), total_score=(2, 2))`

**MATCH**
