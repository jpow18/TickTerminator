"""Needs the `ml` extra."""

import pytest

pytest.importorskip("torch")
pytest.importorskip("torchvision")
pytest.importorskip("transformers")

from tickterminator.detectors.trained import load_thresholds, save_thresholds  # noqa: E402
from tickterminator.pests import Pest  # noqa: E402


def test_thresholds_round_trip(tmp_path):
    save_thresholds(tmp_path, {Pest.TICK: 0.08})
    assert load_thresholds(tmp_path) == {Pest.TICK: 0.08}


def test_model_without_thresholds_file_has_no_saved_thresholds(tmp_path):
    assert load_thresholds(tmp_path) == {}
