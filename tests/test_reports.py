import csv
import json
from pathlib import Path

import pytest
from conftest import save_drone_photo

from tickterminator.pests import Pest
from tickterminator.reports import ReportFormat
from tickterminator.scan import ScanConfig, scan_folder
from tickterminator.survey import Survey


@pytest.fixture
def survey(tmp_path, fake_detector) -> Survey:
    photos = tmp_path / "photos"
    photos.mkdir()
    save_drone_photo(photos / "a.jpg")
    results = list(scan_folder(photos, fake_detector, ScanConfig(pests=list(Pest))))
    return Survey.from_results(results)


def test_for_path_uses_extension():
    assert ReportFormat.for_path(Path("out/REPORT.HTML")) is ReportFormat.HTML


def test_for_path_rejects_unknown_extension():
    with pytest.raises(ValueError, match="Unknown output type"):
        ReportFormat.for_path(Path("report.pdf"))


def test_csv_has_position_and_sector(survey, tmp_path):
    path = tmp_path / "report.csv"
    ReportFormat.CSV.write(survey, path)

    with path.open() as file:
        [row] = list(csv.DictReader(file))
    assert row["pest"] == "tent_caterpillar"
    assert row["sector"] == "1A"
    assert float(row["latitude"]) > 45.5


def test_geojson_has_one_point_per_located_finding(survey, tmp_path):
    path = tmp_path / "report.geojson"
    ReportFormat.GEOJSON.write(survey, path)

    [feature] = json.loads(path.read_text())["features"]
    longitude, latitude = feature["geometry"]["coordinates"]
    assert (latitude, longitude) == (
        feature["properties"]["latitude"],
        feature["properties"]["longitude"],
    )


def test_html_has_thumbnail_and_map_data(survey, tmp_path):
    path = tmp_path / "report.html"
    ReportFormat.HTML.write(survey, path)

    page = path.read_text()
    assert "1 findings in 1 photos" in page
    assert "data:image/jpeg;base64," in page
    assert '"label": "1A"' in page
