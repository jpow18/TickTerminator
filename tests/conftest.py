from collections.abc import Sequence
from pathlib import Path

import pytest
from PIL import ExifTags, Image

from tickterminator.detection import Box, Detection
from tickterminator.pests import Pest


class FakeDetector:
    """Finds one tent in the top-left corner of every image it gets."""

    def __init__(self, score_threshold: float = 0.2) -> None:
        self.score_threshold = score_threshold
        self.image_sizes: list[tuple[int, int]] = []

    def detect(self, image: Image.Image, pests: Sequence[Pest]) -> list[Detection]:
        self.image_sizes.append(image.size)
        return [Detection(Pest.TENT_CATERPILLAR, 0.9, Box(0, 0, 10, 10))]


@pytest.fixture
def fake_detector() -> FakeDetector:
    return FakeDetector()


def dji_xmp(**attributes: str) -> bytes:
    rendered = " ".join(f'drone-dji:{name}="{value}"' for name, value in attributes.items())
    return (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description '
        f'xmlns:drone-dji="http://www.dji.com/drone-dji/1.0/" {rendered}/>'
        "</rdf:RDF></x:xmpmeta>"
    ).encode()


def save_drone_photo(
    path: Path,
    size: tuple[int, int] = (400, 300),
    latitude: tuple[float, float, float] = (45.0, 30.0, 0.0),
    longitude: tuple[float, float, float] = (73.0, 15.0, 0.0),
    focal_length_35mm: int | None = 24,
    **dji: str,
) -> Path:
    """Save a JPEG with the metadata a DJI drone writes. Longitude is west."""
    exif = Image.Exif()
    exif.get_ifd(ExifTags.IFD.GPSInfo).update(
        {
            ExifTags.GPS.GPSLatitudeRef: "N",
            ExifTags.GPS.GPSLatitude: latitude,
            ExifTags.GPS.GPSLongitudeRef: "W",
            ExifTags.GPS.GPSLongitude: longitude,
        }
    )
    if focal_length_35mm:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.FocalLengthIn35mmFilm] = focal_length_35mm
    dji = {"RelativeAltitude": "+30.00", "GimbalPitchDegree": "-90.00", **dji}
    Image.new("RGB", size, "green").save(path, "JPEG", exif=exif, xmp=dji_xmp(**dji))
    return path
