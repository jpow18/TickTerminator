import pytest

from tickterminator.pests import Pest


def test_parse_ignores_case_and_spaces():
    assert Pest.parse(" Tent_Caterpillar ") is Pest.TENT_CATERPILLAR


def test_parse_unknown_pest_lists_choices():
    with pytest.raises(ValueError, match="tent_caterpillar"):
        Pest.parse("dragon")


def test_every_pest_has_prompts():
    assert all(pest.spec.prompts for pest in Pest)
