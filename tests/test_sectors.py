import pytest

from tickterminator.geo import GeoPoint
from tickterminator.sectors import SectorGrid, row_letters

NORTH_WEST = GeoPoint(45.0, -73.0)


@pytest.mark.parametrize(("row", "letters"), [(0, "A"), (25, "Z"), (26, "AA"), (27, "AB")])
def test_row_letters(row, letters):
    assert row_letters(row) == letters


def test_label_counts_columns_east_and_rows_south():
    grid = SectorGrid(NORTH_WEST, size_m=50)
    assert grid.label(NORTH_WEST.offset(north_m=-10, east_m=10)) == "1A"
    assert grid.label(NORTH_WEST.offset(north_m=-60, east_m=310)) == "7B"


def test_covering_uses_north_west_corner():
    points = [GeoPoint(45.0, -72.9), GeoPoint(45.1, -73.0)]
    assert SectorGrid.covering(points, 50).north_west == GeoPoint(45.1, -73.0)


def test_covering_nothing_is_none():
    assert SectorGrid.covering([], 50) is None


def test_corners_contain_the_point():
    grid = SectorGrid(NORTH_WEST, size_m=50)
    point = NORTH_WEST.offset(north_m=-60, east_m=310)
    north_west, south_east = grid.corners(point)
    assert south_east.latitude < point.latitude < north_west.latitude
    assert north_west.longitude < point.longitude < south_east.longitude
