import random
from dataclasses import dataclass
from pathlib import Path

from tickterminator.detection import Box
from tickterminator.labels import Label, LabeledPhoto
from tickterminator.pests import Pest
from tickterminator.tiling import TilingConfig, tile_regions


@dataclass(frozen=True)
class TrainingTile:
    photo_path: Path
    region: Box
    """Tile position in the photo."""
    labels: list[Label]
    """Labels in tile coordinates."""


def photo_tiles(photo: LabeledPhoto, tiling: TilingConfig) -> list[TrainingTile]:
    """Cut a photo into the same tiles the scanner uses. A label goes to each tile that
    contains its center."""
    tiles = []
    for region in tile_regions(*photo.size, tiling):
        width, height = region.x_max - region.x_min, region.y_max - region.y_min
        labels = [
            Label(
                label.pest,
                label.box.shifted(-region.x_min, -region.y_min).clipped(width, height),
            )
            for label in photo.labels
            if region.contains(*label.box.center)
        ]
        tiles.append(TrainingTile(photo.path, region, labels))
    return tiles


def training_tiles(
    photos: list[LabeledPhoto], tiling: TilingConfig, rng: random.Random
) -> list[TrainingTile]:
    """All tiles with labels, plus the same number of empty tiles. Most tiles of a survey are
    empty, so this keeps the model from learning to find nothing."""
    tiles = [tile for photo in photos for tile in photo_tiles(photo, tiling)]
    labeled = [tile for tile in tiles if tile.labels]
    empty = [tile for tile in tiles if not tile.labels]
    return labeled + rng.sample(empty, min(len(empty), max(len(labeled), 1)))


def pests_in(photos: list[LabeledPhoto]) -> list[Pest]:
    found = {label.pest for photo in photos for label in photo.labels}
    return [pest for pest in Pest if pest in found]
