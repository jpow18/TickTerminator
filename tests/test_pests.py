import pytest

from tickterminator.pests import Pest, View


def test_parse_ignores_case_and_spaces():
    assert Pest.parse(" Tent_Caterpillar ") is Pest.TENT_CATERPILLAR


def test_parse_unknown_pest_lists_choices():
    with pytest.raises(ValueError, match="tent_caterpillar"):
        Pest.parse("dragon")


def test_every_pest_has_prompts():
    assert all(pest.spec.prompts for pest in Pest)


def test_for_view_separates_drone_and_close_up_pests():
    assert Pest.TENT_CATERPILLAR in Pest.for_view(View.AERIAL)
    assert Pest.for_view(View.CLOSE_UP) == [Pest.TICK]
