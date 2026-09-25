import csv

import pytest
from PIL import Image

from tickterminator import cli
from tickterminator.detectors import DetectorKind


@pytest.fixture
def photo_folder(tmp_path):
    folder = tmp_path / "photos"
    folder.mkdir()
    Image.new("RGB", (64, 64)).save(folder / "photo.jpg")
    return folder


@pytest.fixture(autouse=True)
def use_fake_detector(monkeypatch, fake_detector):
    monkeypatch.setattr(DetectorKind, "create", lambda self, **options: fake_detector)


def test_scan_writes_csv_report(photo_folder, tmp_path):
    output = tmp_path / "report.csv"
    cli.main(["scan", str(photo_folder), "--output", str(output), "--pests", "tent_caterpillar"])

    with output.open() as file:
        rows = list(csv.DictReader(file))
    assert rows == [
        {
            "image": (photo_folder / "photo.jpg").as_posix(),
            "pest": "tent_caterpillar",
            "score": "0.9",
            "x_min": "0",
            "y_min": "0",
            "x_max": "10",
            "y_max": "10",
            "latitude": "",
            "longitude": "",
            "sector": "",
        }
    ]


def test_scan_rejects_unknown_pest(photo_folder, capsys):
    with pytest.raises(SystemExit):
        cli.main(["scan", str(photo_folder), "--pests", "dragon"])
    assert "Unknown pest" in capsys.readouterr().err


def test_scan_rejects_unknown_output_type(photo_folder, tmp_path, capsys):
    with pytest.raises(SystemExit):
        cli.main(["scan", str(photo_folder), "--output", str(tmp_path / "report.pdf")])
    assert "Unknown output type" in capsys.readouterr().err


def test_pests_command_lists_all_pests(capsys):
    cli.main(["pests"])
    assert "tent_caterpillar" in capsys.readouterr().out


def test_scan_writes_default_reports(photo_folder, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.main(["scan", str(photo_folder)])
    assert (tmp_path / "detections.csv").exists()
    assert (tmp_path / "report.html").exists()
