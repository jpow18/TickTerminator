import pytest
from conftest import save_drone_photo
from PIL import Image

from tickterminator.photos import find_photos, load_photo


def test_find_photos_includes_subfolders_and_ignores_other_files(tmp_path):
    (tmp_path / "flight1").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "flight1" / "a.JPG")
    Image.new("RGB", (8, 8)).save(tmp_path / "b.png")
    (tmp_path / "notes.txt").write_text("not a photo")

    assert [path.name for path in find_photos(tmp_path)] == ["b.png", "a.JPG"]


def test_load_photo_reads_dji_pose(tmp_path):
    path = save_drone_photo(tmp_path / "dji.jpg", GimbalYawDegree="-12.50")
    pose = load_photo(path).pose

    assert pose.position.latitude == pytest.approx(45.5)
    assert pose.position.longitude == pytest.approx(-73.25)
    assert pose.altitude_m == 30.0
    assert pose.yaw_deg == -12.5
    assert pose.focal_length_35mm == 24.0


def test_oblique_photo_has_no_pose(tmp_path):
    path = save_drone_photo(tmp_path / "oblique.jpg", GimbalPitchDegree="-45.00")
    assert load_photo(path).pose is None


def test_fallback_altitude_is_used_when_photo_has_none(tmp_path):
    path = save_drone_photo(tmp_path / "no_altitude.jpg", RelativeAltitude="0")
    assert load_photo(path).pose is None
    assert load_photo(path, fallback_altitude_m=40.0).pose.altitude_m == 40.0


def test_photo_without_metadata_has_no_pose(tmp_path):
    path = tmp_path / "plain.jpg"
    Image.new("RGB", (8, 8)).save(path)
    assert load_photo(path).pose is None
