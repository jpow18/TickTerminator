import string
from collections.abc import Iterable
from dataclasses import dataclass

from tickterminator.geo import GeoPoint


def row_letters(row: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA, like spreadsheet columns."""
    letters = ""
    row += 1
    while row:
        row, remainder = divmod(row - 1, 26)
        letters = string.ascii_uppercase[remainder] + letters
    return letters


@dataclass(frozen=True)
class SectorGrid:
    """Square sectors. Columns are numbers from west to east. Rows are letters from north to south.

    Sector "7B" is the seventh column and the second row.
    """

    north_west: GeoPoint
    size_m: float

    @classmethod
    def covering(cls, points: Iterable[GeoPoint], size_m: float) -> "SectorGrid | None":
        points = list(points)
        if not points:
            return None
        north = max(point.latitude for point in points)
        west = min(point.longitude for point in points)
        return cls(GeoPoint(north, west), size_m)

    def cell(self, point: GeoPoint) -> tuple[int, int]:
        """Return (column, row), both from 0."""
        north_m, east_m = self.north_west.meters_to(point)
        return int(max(east_m, 0.0) // self.size_m), int(max(-north_m, 0.0) // self.size_m)

    def label(self, point: GeoPoint) -> str:
        column, row = self.cell(point)
        return f"{column + 1}{row_letters(row)}"

    def corners(self, point: GeoPoint) -> tuple[GeoPoint, GeoPoint]:
        """Return the north-west and south-east corners of the sector that contains `point`."""
        column, row = self.cell(point)
        north_west = self.north_west.offset(-row * self.size_m, column * self.size_m)
        return north_west, north_west.offset(-self.size_m, self.size_m)
