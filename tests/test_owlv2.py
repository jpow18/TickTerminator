"""Needs the `ml` extra. The model weights are not downloaded."""

import pytest

pytest.importorskip("torch")
pytest.importorskip("torchvision")
pytest.importorskip("transformers")

from tickterminator.detectors.owlv2 import Owlv2Detector  # noqa: E402
from tickterminator.pests import Pest  # noqa: E402


def detector_with_threshold(score_threshold: float | None) -> Owlv2Detector:
    detector = Owlv2Detector.__new__(Owlv2Detector)
    detector._score_threshold = score_threshold
    return detector


def test_each_pest_uses_its_own_min_score_by_default():
    detector = detector_with_threshold(None)
    assert detector._min_score(Pest.PINE_PROCESSIONARY) == Pest.PINE_PROCESSIONARY.spec.min_score
    assert detector._min_score(Pest.TICK) == Pest.TICK.spec.min_score


def test_score_threshold_overrides_all_pests():
    detector = detector_with_threshold(0.5)
    assert {detector._min_score(pest) for pest in Pest} == {0.5}


def test_prompts_replace_the_prompts_of_one_pest():
    detector = detector_with_threshold(None)
    detector._prompts = {Pest.TICK: ("black dot",)}
    assert detector._prompts_for(Pest.TICK) == ("black dot",)
    assert detector._prompts_for(Pest.BAGWORM) == Pest.BAGWORM.spec.prompts
