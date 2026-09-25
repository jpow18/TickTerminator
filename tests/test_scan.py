from PIL import Image

from tickterminator.detection import Box
from tickterminator.pests import Pest
from tickterminator.scan import scan_folder, scan_image
from tickterminator.tiling import TilingConfig


def test_scan_image_converts_tile_boxes_to_image_coordinates(fake_detector):
    image = Image.new("RGB", (800, 400))
    detections = scan_image(image, fake_detector, list(Pest), TilingConfig(400, 0))

    assert fake_detector.image_sizes == [(400, 400), (400, 400)]
    assert {detection.box for detection in detections} == {
        Box(0, 0, 10, 10),
        Box(400, 0, 410, 10),
    }


def test_scan_folder_finds_images_in_subfolders(tmp_path, fake_detector):
    (tmp_path / "flight1").mkdir()
    Image.new("RGB", (64, 64)).save(tmp_path / "flight1" / "a.JPG")
    Image.new("RGB", (64, 64)).save(tmp_path / "b.png")
    (tmp_path / "notes.txt").write_text("not an image")

    results = list(scan_folder(tmp_path, fake_detector, list(Pest), TilingConfig()))

    assert [result.image_path.name for result in results] == ["b.png", "a.JPG"]
