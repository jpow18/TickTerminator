import pytest

from tickterminator.geo import CameraPose, GeoPoint

START = GeoPoint(45.0, -73.0)


def pose(yaw_deg: float = 0.0) -> CameraPose:
    return CameraPose(START, altitude_m=100.0, yaw_deg=yaw_deg, focal_length_35mm=24.0)


def test_offset_and_meters_to_are_inverse():
    north_m, east_m = START.meters_to(START.offset(north_m=120.0, east_m=-40.0))
    assert north_m == pytest.approx(120.0, abs=0.01)
    assert east_m == pytest.approx(-40.0, abs=0.01)


def test_meters_per_pixel():
    # Ground diagonal = 100 m * 43.27 mm / 24 mm = 180.3 m, image diagonal = 5000 px.
    assert pose().meters_per_pixel(4000, 3000) == pytest.approx(180.29 / 5000, rel=1e-3)


def test_image_center_is_camera_position():
    located = pose().locate(2000, 1500, 4000, 3000)
    assert located.latitude == pytest.approx(START.latitude)
    assert located.longitude == pytest.approx(START.longitude)


@pytest.mark.parametrize(
    ("yaw_deg", "expected_direction"),
    [(0, (1, 0)), (90, (0, 1)), (180, (-1, 0)), (-90, (0, -1))],
)
def test_image_top_points_in_yaw_direction(yaw_deg, expected_direction):
    camera = pose(yaw_deg)
    north_m, east_m = START.meters_to(camera.locate(2000, 0, 4000, 3000))
    distance_m = 1500 * camera.meters_per_pixel(4000, 3000)
    assert north_m == pytest.approx(expected_direction[0] * distance_m, abs=0.01)
    assert east_m == pytest.approx(expected_direction[1] * distance_m, abs=0.01)
