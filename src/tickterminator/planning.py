"""Plan a survey flight: how high to fly so that the targets are large enough in the photos."""

from dataclasses import dataclass
from enum import Enum

from tickterminator.geo import ground_sample_distance_m

MAX_LEGAL_ALTITUDE_M = 120.0
"""The usual limit for small drones in the US (400 ft) and the EU."""
DEFAULT_PIXELS_ACROSS = 10
DEFAULT_OVERLAP = 0.8


@dataclass(frozen=True)
class Camera:
    name: str
    focal_length_35mm: float
    width_px: int
    height_px: int

    def meters_per_pixel(self, altitude_m: float) -> float:
        return ground_sample_distance_m(
            altitude_m, self.focal_length_35mm, self.width_px, self.height_px
        )

    def altitude_for(self, meters_per_pixel: float) -> float:
        return meters_per_pixel / self.meters_per_pixel(1.0)


class CameraModel(Enum):
    """Common drone cameras. To add a camera, add a member."""

    DJI_MINI_4_PRO = Camera("DJI Mini 4 Pro (12 MP)", 24, 4032, 3024)
    DJI_AIR_3 = Camera("DJI Air 3 (12 MP, wide camera)", 24, 4032, 3024)
    DJI_MAVIC_3 = Camera("DJI Mavic 3", 24, 5280, 3956)
    DJI_MAVIC_2_PRO = Camera("DJI Mavic 2 Pro", 28, 5472, 3648)
    DJI_PHANTOM_4_PRO = Camera("DJI Phantom 4 Pro", 24, 5472, 3648)

    @property
    def camera(self) -> Camera:
        return self.value


@dataclass(frozen=True)
class FlightPlan:
    camera: Camera
    target_size_m: float
    altitude_m: float
    meters_per_pixel: float
    overlap: float

    @property
    def footprint_m(self) -> tuple[float, float]:
        """Ground width and height of one photo."""
        return (
            self.camera.width_px * self.meters_per_pixel,
            self.camera.height_px * self.meters_per_pixel,
        )

    @property
    def photo_spacing_m(self) -> float:
        """Distance between photos along a flight line. The drone flies toward the image top."""
        return self.footprint_m[1] * (1 - self.overlap)

    @property
    def line_spacing_m(self) -> float:
        return self.footprint_m[0] * (1 - self.overlap)

    @property
    def exceeds_legal_altitude(self) -> bool:
        return self.altitude_m > MAX_LEGAL_ALTITUDE_M


def plan_flight(
    camera: Camera,
    target_size_m: float,
    pixels_across: int = DEFAULT_PIXELS_ACROSS,
    overlap: float = DEFAULT_OVERLAP,
) -> FlightPlan:
    """The highest flight that shows a target of `target_size_m` with `pixels_across` pixels."""
    if target_size_m <= 0 or pixels_across <= 0:
        raise ValueError("Target size and pixels across must be positive.")
    if not 0 <= overlap < 1:
        raise ValueError("Overlap must be at least 0 and less than 1.")
    meters_per_pixel = target_size_m / pixels_across
    return FlightPlan(
        camera=camera,
        target_size_m=target_size_m,
        altitude_m=camera.altitude_for(meters_per_pixel),
        meters_per_pixel=meters_per_pixel,
        overlap=overlap,
    )
