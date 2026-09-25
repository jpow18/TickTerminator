from collections.abc import Iterator
from dataclasses import astuple, dataclass

from PIL import Image

from tickterminator.detection import Box


@dataclass(frozen=True)
class TilingConfig:
    """Cut large photos into tiles so small targets stay visible to the detector."""

    tile_size: int = 1024
    overlap: int = 128

    def __post_init__(self) -> None:
        if self.tile_size <= 0:
            raise ValueError("tile_size must be positive")
        if not 0 <= self.overlap < self.tile_size:
            raise ValueError("overlap must be at least 0 and less than tile_size")


@dataclass(frozen=True)
class Tile:
    image: Image.Image
    x_offset: int
    y_offset: int


def tile_starts(length: int, tile_size: int, overlap: int) -> list[int]:
    """Start positions along one axis. The last tile ends at the image edge."""
    if length <= tile_size:
        return [0]
    stride = tile_size - overlap
    return [*range(0, length - tile_size, stride), length - tile_size]


def tile_regions(width: int, height: int, config: TilingConfig) -> list[Box]:
    return [
        Box(x, y, min(x + config.tile_size, width), min(y + config.tile_size, height))
        for y in tile_starts(height, config.tile_size, config.overlap)
        for x in tile_starts(width, config.tile_size, config.overlap)
    ]


def iter_tiles(image: Image.Image, config: TilingConfig) -> Iterator[Tile]:
    for region in tile_regions(*image.size, config):
        yield Tile(image.crop(astuple(region)), int(region.x_min), int(region.y_min))
