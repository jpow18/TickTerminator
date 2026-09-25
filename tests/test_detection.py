import pytest

from tickterminator.detection import Box, Detection, suppress_duplicates
from tickterminator.pests import Pest


def test_iou_of_identical_boxes_is_one():
    box = Box(0, 0, 10, 10)
    assert box.iou(box) == 1


def test_iou_of_half_overlap():
    assert Box(0, 0, 10, 10).iou(Box(5, 0, 15, 10)) == pytest.approx(1 / 3)


def test_iou_of_separate_boxes_is_zero():
    assert Box(0, 0, 10, 10).iou(Box(20, 20, 30, 30)) == 0


def test_clipped_keeps_box_inside_image():
    assert Box(-5, -5, 50, 50).clipped(40, 30) == Box(0, 0, 40, 30)


def test_suppress_duplicates_keeps_highest_score():
    low = Detection(Pest.TENT_CATERPILLAR, 0.3, Box(0, 0, 10, 10))
    high = Detection(Pest.TENT_CATERPILLAR, 0.8, Box(1, 1, 11, 11))
    assert suppress_duplicates([low, high], iou_threshold=0.5) == [high]


def test_suppress_duplicates_keeps_different_pests():
    tent = Detection(Pest.TENT_CATERPILLAR, 0.3, Box(0, 0, 10, 10))
    webworm = Detection(Pest.FALL_WEBWORM, 0.8, Box(0, 0, 10, 10))
    assert len(suppress_duplicates([tent, webworm], iou_threshold=0.5)) == 2


def test_expanded_adds_fraction_on_each_side():
    assert Box(10, 10, 20, 30).expanded(0.5) == Box(5, 0, 25, 40)
