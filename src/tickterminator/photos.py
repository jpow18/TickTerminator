import re
from dataclasses import dataclass
from pathlib import Path

from PIL import ExifTags, Image, ImageOps

from tickterminator.geo import CameraPose, GeoPoint

PHOTO_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff"})
NADIR_PITCH_DEG = -90.0
NADIR_TOLERANCE_DEG = 10.0

_DJI_XMP_ATTRIBUTE = re.compile(r'drone-dji:(\w+)="([^"]*)"')


@dataclass(frozen=True)
class Photo:
    path: Path
    image: Image.Image
    pose: CameraPose | None
    """None if the photo has no usable position data. Then detections have no map position."""


def find_photos(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in PHOTO_SUFFIXES
    )


def load_photo(path: Path, fallback_altitude_m: float | None = None) -> Photo:
    with Image.open(path) as source:
        pose = read_camera_pose(source, fallback_altitude_m)
        image = upright_rgb(source)
    return Photo(path, image, pose)


def load_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        return upright_rgb(source)


def upright_rgb(image: Image.Image) -> Image.Image:
    return ImageOps.exif_transpose(image).convert("RGB")


def read_camera_pose(image: Image.Image, fallback_altitude_m: float | None) -> CameraPose | None:
    exif = image.getexif()
    position = read_gps_position(exif.get_ifd(ExifTags.IFD.GPSInfo))
    focal_length_35mm = exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.FocalLengthIn35mmFilm)
    dji = read_dji_xmp(image)

    recorded_altitude_m = float(dji.get("RelativeAltitude", 0.0))
    altitude_m = recorded_altitude_m if recorded_altitude_m > 0 else fallback_altitude_m
    pitch_deg = float(dji.get("GimbalPitchDegree", NADIR_PITCH_DEG))
    yaw_deg = float(dji.get("GimbalYawDegree", dji.get("FlightYawDegree", 0.0)))

    if position is None or not focal_length_35mm or not altitude_m:
        return None
    if abs(pitch_deg - NADIR_PITCH_DEG) > NADIR_TOLERANCE_DEG:
        return None
    return CameraPose(position, altitude_m, yaw_deg, float(focal_length_35mm))


def read_gps_position(gps: dict) -> GeoPoint | None:
    try:
        latitude = dms_to_degrees(gps[ExifTags.GPS.GPSLatitude])
        longitude = dms_to_degrees(gps[ExifTags.GPS.GPSLongitude])
    except (KeyError, TypeError, ValueError):
        return None
    if gps.get(ExifTags.GPS.GPSLatitudeRef) == "S":
        latitude = -latitude
    if gps.get(ExifTags.GPS.GPSLongitudeRef) == "W":
        longitude = -longitude
    return GeoPoint(latitude, longitude)


def dms_to_degrees(dms: tuple) -> float:
    degrees, minutes, seconds = (float(value) for value in dms)
    return degrees + minutes / 60 + seconds / 3600


def read_dji_xmp(image: Image.Image) -> dict[str, str]:
    """Read DJI drone attributes, for example RelativeAltitude and GimbalYawDegree."""
    xmp = image.info.get("xmp", b"")
    if isinstance(xmp, bytes):
        xmp = xmp.decode("utf-8", errors="ignore")
    return dict(_DJI_XMP_ATTRIBUTE.findall(xmp))
