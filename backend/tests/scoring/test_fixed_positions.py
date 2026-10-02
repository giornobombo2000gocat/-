import pytest

from examples.scoring_positions import actual_score, fixed_positions


@pytest.mark.parametrize("position", fixed_positions(), ids=lambda p: p.name)
def test_fixed_position_matches_all_expected_categories(position):
    assert actual_score(position.state) == position.expected
    assert actual_score(position.state) == position.expected  # No repeat scoring side effects.
