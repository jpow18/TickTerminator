import csv

import pytest
from conftest import FakeDetector
from PIL import Image

from tickterminator import cli
from tickterminator.detectors import DetectorKind
from tickterminator.pests import Pest


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


def test_scan_skips_close_up_pests_by_default(photo_folder, tmp_path, fake_detector):
    pests_seen = []
    fake_detector.detect = lambda image, pests: pests_seen.append(list(pests)) or []
    cli.main(["scan", str(photo_folder), "--output", str(tmp_path / "report.csv")])
    assert "TICK" not in {pest.name for pest in pests_seen[0]}


def test_prompt_replaces_the_prompts_of_one_pest(photo_folder, tmp_path, monkeypatch):
    options_seen = {}

    def create(self, **options):
        options_seen.update(options)
        return FakeDetector()

    monkeypatch.setattr(DetectorKind, "create", create)
    cli.main(
        ["scan", str(photo_folder), "--pests", "tick", "--prompt", "black dot",
         "--prompt", "tick", "--output", str(tmp_path / "report.csv")]
    )  # fmt: skip
    assert options_seen["prompts"] == {Pest.TICK: ("black dot", "tick")}


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--pests", "tick,bagworm"], "exactly one pest"),
        (["--pests", "tick", "--detector", "trained"], "only with the OWLV2"),
    ],
)
def test_prompt_needs_one_pest_and_owlv2(photo_folder, capsys, arguments, message):
    with pytest.raises(SystemExit):
        cli.main(["scan", str(photo_folder), "--prompt", "black dot", *arguments])
    assert message in capsys.readouterr().err
