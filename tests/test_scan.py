from conftest import save_drone_photo
from PIL import Image

from tickterminator.detection import Box
from tickterminator.pests import Pest
from tickterminator.scan import ScanConfig, scan_folder, scan_image
from tickterminator.tiling import TilingConfig


def test_scan_image_converts_tile_boxes_to_image_coordinates(fake_detector):
    image = Image.new("RGB", (800, 400))
    detections = scan_image(image, fake_detector, list(Pest), TilingConfig(400, 0))

    assert fake_detector.image_sizes == [(400, 400), (400, 400)]
    assert {detection.box for detection in detections} == {
        Box(0, 0, 10, 10),
        Box(400, 0, 410, 10),
    }


def test_scan_folder_locates_findings_on_geotagged_photos(tmp_path, fake_detector):
    save_drone_photo(tmp_path / "geotagged.jpg")
    Image.new("RGB", (64, 64)).save(tmp_path / "plain.jpg")

    results = list(scan_folder(tmp_path, fake_detector, ScanConfig(pests=list(Pest))))

    located = {result.path.name: result.findings[0].location for result in results}
    assert located["plain.jpg"] is None
    # The fake finding is in the top-left corner, so it is north-west of the camera.
    assert located["geotagged.jpg"].latitude > 45.5
    assert located["geotagged.jpg"].longitude < -73.25
