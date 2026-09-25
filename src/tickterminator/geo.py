import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_000.0
FULL_FRAME_DIAGONAL_MM = 43.27


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float

    def offset(self, north_m: float, east_m: float) -> "GeoPoint":
        return GeoPoint(
            self.latitude + math.degrees(north_m / EARTH_RADIUS_M),
            self.longitude
            + math.degrees(east_m / (EARTH_RADIUS_M * math.cos(math.radians(self.latitude)))),
        )

    def meters_to(self, other: "GeoPoint") -> tuple[float, float]:
        """Return (north_m, east_m) from this point to `other`. Accurate for short distances."""
        north_m = math.radians(other.latitude - self.latitude) * EARTH_RADIUS_M
        east_m = (
            math.radians(other.longitude - self.longitude)
            * EARTH_RADIUS_M
            * math.cos(math.radians(self.latitude))
        )
        return north_m, east_m


@dataclass(frozen=True)
class CameraPose:
    """Position of a camera that points straight down."""

    position: GeoPoint
    altitude_m: float
    """Height above the ground, not above sea level."""
    yaw_deg: float
    """Direction of the image top, clockwise from north."""
    focal_length_35mm: float

    def meters_per_pixel(self, width: int, height: int) -> float:
        ground_diagonal_m = self.altitude_m * FULL_FRAME_DIAGONAL_MM / self.focal_length_35mm
        return ground_diagonal_m / math.hypot(width, height)

    def locate(self, x: float, y: float, width: int, height: int) -> GeoPoint:
        """Ground position of pixel (x, y). Assumes flat ground."""
        scale = self.meters_per_pixel(width, height)
        forward_m = (height / 2 - y) * scale
        right_m = (x - width / 2) * scale
        yaw = math.radians(self.yaw_deg)
        north_m = forward_m * math.cos(yaw) - right_m * math.sin(yaw)
        east_m = forward_m * math.sin(yaw) + right_m * math.cos(yaw)
        return self.position.offset(north_m, east_m)
