import json
from pathlib import Path

import pytest
from PIL import Image

from tickterminator import cli
from tickterminator.detection import Box, Detection
from tickterminator.detectors import DetectorKind
from tickterminator.evaluation import (
    Counts,
    PhotoDetections,
    best_threshold,
    match_boxes,
    match_presence,
    score,
)
from tickterminator.labels import Label, LabeledPhoto
from tickterminator.pests import Pest

TENT = Pest.TENT_CATERPILLAR


def detection(box: Box, score_value: float = 0.9, pest: Pest = TENT) -> Detection:
    return Detection(pest, score_value, box)


def test_counts_metrics():
    counts = Counts(true_positives=3, false_positives=1, false_negatives=3)
    assert counts.precision == 0.75
    assert counts.recall == 0.5
    assert counts.f1 == pytest.approx(0.6)


def test_empty_counts_have_zero_metrics():
    assert (Counts().precision, Counts().recall, Counts().f1) == (0.0, 0.0, 0.0)


def test_match_boxes_counts_each_label_once():
    label = Label(TENT, Box(0, 0, 10, 10))
    duplicates = [detection(Box(0, 0, 10, 10)), detection(Box(1, 0, 11, 10), 0.5)]
    assert match_boxes(duplicates, [label], iou_threshold=0.5) == Counts(1, 1, 0)


def test_match_boxes_needs_enough_overlap():
    label = Label(TENT, Box(0, 0, 10, 10))
    assert match_boxes([detection(Box(8, 8, 18, 18))], [label], 0.5) == Counts(0, 1, 1)


@pytest.mark.parametrize(
    ("detected", "labeled", "expected"),
    [(True, True, Counts(1, 0, 0)), (True, False, Counts(0, 1, 0)), (False, True, Counts(0, 0, 1))],
)
def test_match_presence(detected, labeled, expected):
    assert match_presence(detected, labeled) == expected


def test_score_filters_by_pest_and_min_score():
    photo = LabeledPhoto(Path("a.jpg"), (100, 100), [Label(TENT, Box(0, 0, 10, 10))])
    detections = [
        detection(Box(0, 0, 10, 10), 0.3),
        detection(Box(50, 50, 60, 60), 0.9, Pest.DEFOLIATION),
    ]
    results = [PhotoDetections(photo, detections)]

    assert score(results, TENT, min_score=0.2).boxes == Counts(1, 0, 0)
    assert score(results, TENT, min_score=0.5).boxes == Counts(0, 0, 1)
    assert score(results, TENT, min_score=0.5).photos == Counts(0, 0, 1)


def test_evaluate_command_prints_scores(tmp_path, monkeypatch, fake_detector, capsys):
    monkeypatch.setattr(DetectorKind, "create", lambda self, **options: fake_detector)
    Image.new("RGB", (64, 64)).save(tmp_path / "a.jpg")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "images": [{"id": 1, "file_name": "a.jpg", "width": 64, "height": 64}],
                "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 10, 10]}],
                "categories": [{"id": 1, "name": "tent_caterpillar"}],
            }
        )
    )

    cli.main(["evaluate", str(labels), "--images", str(tmp_path), "--thresholds", "0.5,0.95"])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "1 photos, 1 labels"
    assert lines[2].split() == [
        "tent_caterpillar",
        "0.50",
        "1",
        "1",
        "1",
        "1.00",
        "1.00",
        "1.00",
        "1.00",
    ]
    assert lines[3].split() == [
        "tent_caterpillar",
        "0.95",
        "1",
        "0",
        "0",
        "0.00",
        "0.00",
        "0.00",
        "0.00",
    ]


def test_evaluate_rejects_bad_thresholds(tmp_path, capsys):
    with pytest.raises(SystemExit):
        cli.main(["evaluate", "labels.json", "--images", str(tmp_path), "--thresholds", "high"])
    assert "Not a list of numbers" in capsys.readouterr().err


def test_best_threshold_drops_low_scores_that_are_wrong():
    label = Label(TENT, Box(0, 0, 10, 10))
    photo = LabeledPhoto(Path("a.jpg"), (100, 100), [label])
    detections = [detection(Box(0, 0, 10, 10), 0.3), detection(Box(50, 50, 60, 60), 0.1)]
    results = [PhotoDetections(photo, detections)]

    best = best_threshold(results, TENT, [0.05, 0.2, 0.5])

    assert best.min_score == 0.2
    assert best.boxes.f1 == 1.0
