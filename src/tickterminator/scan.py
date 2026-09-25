from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from tickterminator.detection import Detection, suppress_duplicates
from tickterminator.detectors import Detector
from tickterminator.geo import CameraPose, GeoPoint
from tickterminator.pests import Pest
from tickterminator.photos import Photo, find_photos, load_photo
from tickterminator.tiling import TilingConfig, iter_tiles

DUPLICATE_IOU_THRESHOLD = 0.5


@dataclass(frozen=True)
class ScanConfig:
    pests: Sequence[Pest]
    tiling: TilingConfig = TilingConfig()
    fallback_altitude_m: float | None = None


@dataclass(frozen=True)
class Finding:
    detection: Detection
    location: GeoPoint | None


@dataclass(frozen=True)
class PhotoResult:
    path: Path
    size: tuple[int, int]
    pose: CameraPose | None
    findings: list[Finding]


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


def scan_photo(photo: Photo, detector: Detector, config: ScanConfig) -> PhotoResult:
    detections = scan_image(photo.image, detector, config.pests, config.tiling)
    return PhotoResult(
        photo.path,
        photo.image.size,
        photo.pose,
        [Finding(detection, locate(detection, photo)) for detection in detections],
    )


def locate(detection: Detection, photo: Photo) -> GeoPoint | None:
    if photo.pose is None:
        return None
    return photo.pose.locate(*detection.box.center, *photo.image.size)


def scan_paths(
    paths: Sequence[Path], detector: Detector, config: ScanConfig
) -> Iterator[PhotoResult]:
    for path in paths:
        yield scan_photo(load_photo(path, config.fallback_altitude_m), detector, config)


def scan_folder(folder: Path, detector: Detector, config: ScanConfig) -> Iterator[PhotoResult]:
    return scan_paths(find_photos(folder), detector, config)
