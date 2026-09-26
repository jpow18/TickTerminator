import pytest

from tickterminator import cli
from tickterminator.geo import CameraPose, GeoPoint
from tickterminator.planning import Camera, CameraModel, plan_flight

CAMERA = Camera("test camera", focal_length_35mm=24, width_px=4000, height_px=3000)


def test_plan_gives_the_requested_ground_resolution():
    flight = plan_flight(CAMERA, target_size_m=0.10, pixels_across=10)
    assert flight.meters_per_pixel == pytest.approx(0.01)
    assert CAMERA.meters_per_pixel(flight.altitude_m) == pytest.approx(0.01)


def test_plan_matches_the_scanner_geometry():
    flight = plan_flight(CAMERA, target_size_m=0.10)
    pose = CameraPose(GeoPoint(45, -73), flight.altitude_m, 0, CAMERA.focal_length_35mm)
    assert pose.meters_per_pixel(4000, 3000) == pytest.approx(flight.meters_per_pixel)


def test_footprint_and_spacing():
    flight = plan_flight(CAMERA, target_size_m=0.10, pixels_across=10, overlap=0.8)
    assert flight.footprint_m == pytest.approx((40.0, 30.0))
    assert flight.photo_spacing_m == pytest.approx(6.0)
    assert flight.line_spacing_m == pytest.approx(8.0)


def test_high_plan_exceeds_legal_altitude():
    assert plan_flight(CAMERA, target_size_m=2.0).exceeds_legal_altitude
    assert not plan_flight(CAMERA, target_size_m=0.1).exceeds_legal_altitude


@pytest.mark.parametrize(("size", "pixels", "overlap"), [(0, 10, 0.8), (0.1, 0, 0.8), (0.1, 10, 1)])
def test_invalid_plan_is_rejected(size, pixels, overlap):
    with pytest.raises(ValueError):
        plan_flight(CAMERA, size, pixels, overlap)


def test_every_camera_model_has_a_valid_camera():
    assert all(model.camera.focal_length_35mm > 0 for model in CameraModel)


def test_plan_command_with_camera_model(capsys):
    cli.main(["plan", "--target-cm", "10", "--camera", "dji_mini_4_pro"])
    output = capsys.readouterr().out
    assert "Fly at most 28 m above the tree tops." in output
    assert "1.00 cm per pixel" in output


def test_plan_command_with_custom_camera(capsys):
    cli.main(["plan", "--target-cm", "10", "--focal-length", "24", "--image-size", "4000x3000"])
    assert "custom camera" in capsys.readouterr().out


def test_plan_command_needs_a_camera(capsys):
    with pytest.raises(SystemExit):
        cli.main(["plan", "--target-cm", "10"])
    assert "Give --camera" in capsys.readouterr().err
