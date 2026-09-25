from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from tickterminator.detection import Detection, suppress_duplicates
from tickterminator.detectors import Detector
from tickterminator.images import find_images, load_image
from tickterminator.pests import Pest
from tickterminator.tiling import TilingConfig, iter_tiles

DUPLICATE_IOU_THRESHOLD = 0.5


@dataclass(frozen=True)
class ImageResult:
    image_path: Path
    detections: list[Detection]


def scan_image(
    image: Image.Image,
    detector: Detector,
    pests: Sequence[Pest],
    tiling: TilingConfig,
) -> list[Detection]:
    detections = [
        detection.shifted(tile.x_offset, tile.y_offset)
        for tile in iter_tiles(image, tiling)
        for detection in detector.detect(tile.image, pests)
    ]
    return suppress_duplicates(detections, DUPLICATE_IOU_THRESHOLD)


def scan_folder(
    folder: Path,
    detector: Detector,
    pests: Sequence[Pest],
    tiling: TilingConfig,
) -> Iterator[ImageResult]:
    for path in find_images(folder):
        yield ImageResult(path, scan_image(load_image(path), detector, pests, tiling))
