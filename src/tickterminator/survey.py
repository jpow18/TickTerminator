from collections.abc import Iterator
from dataclasses import dataclass

from tickterminator.scan import Finding, PhotoResult
from tickterminator.sectors import SectorGrid

DEFAULT_SECTOR_SIZE_M = 50.0


@dataclass(frozen=True)
class Survey:
    """All results of one flight, with a sector grid over the flight area."""

    photos: list[PhotoResult]
    grid: SectorGrid | None

    @classmethod
    def from_results(
        cls, photos: list[PhotoResult], sector_size_m: float = DEFAULT_SECTOR_SIZE_M
    ) -> "Survey":
        points = [photo.pose.position for photo in photos if photo.pose] + [
            finding.location for photo in photos for finding in photo.findings if finding.location
        ]
        return cls(photos, SectorGrid.covering(points, sector_size_m))

    def findings(self) -> Iterator[tuple[PhotoResult, Finding]]:
        for photo in self.photos:
            for finding in photo.findings:
                yield photo, finding

    def sector(self, finding: Finding) -> str | None:
        if self.grid is None or finding.location is None:
            return None
        return self.grid.label(finding.location)
