from dataclasses import dataclass

from tickterminator.pests import Pest


@dataclass(frozen=True)
class Box:
    """Pixel coordinates. The origin is the top-left corner of the image."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def area(self) -> float:
        return max(0.0, self.x_max - self.x_min) * max(0.0, self.y_max - self.y_min)

    @property
    def center(self) -> tuple[float, float]:
        return (self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x < self.x_max and self.y_min <= y < self.y_max

    def expanded(self, fraction: float) -> "Box":
        """Add `fraction` of the box width and height on each side."""
        dx = (self.x_max - self.x_min) * fraction
        dy = (self.y_max - self.y_min) * fraction
        return Box(self.x_min - dx, self.y_min - dy, self.x_max + dx, self.y_max + dy)

    def shifted(self, dx: float, dy: float) -> "Box":
        return Box(self.x_min + dx, self.y_min + dy, self.x_max + dx, self.y_max + dy)

    def clipped(self, width: float, height: float) -> "Box":
        return Box(
            min(max(self.x_min, 0.0), width),
            min(max(self.y_min, 0.0), height),
            min(max(self.x_max, 0.0), width),
            min(max(self.y_max, 0.0), height),
        )

    def iou(self, other: "Box") -> float:
        overlap = Box(
            max(self.x_min, other.x_min),
            max(self.y_min, other.y_min),
            min(self.x_max, other.x_max),
            min(self.y_max, other.y_max),
        ).area
        union = self.area + other.area - overlap
        return overlap / union if union > 0 else 0.0


@dataclass(frozen=True)
class Detection:
    pest: Pest
    score: float
    box: Box

    def shifted(self, dx: float, dy: float) -> "Detection":
        return Detection(self.pest, self.score, self.box.shifted(dx, dy))


def suppress_duplicates(detections: list[Detection], iou_threshold: float) -> list[Detection]:
    """Keep the highest-score detection where boxes of the same pest overlap."""
    kept: list[Detection] = []
    for candidate in sorted(detections, key=lambda d: d.score, reverse=True):
        if all(
            kept_detection.pest != candidate.pest
            or kept_detection.box.iou(candidate.box) < iou_threshold
            for kept_detection in kept
        ):
            kept.append(candidate)
    return kept
