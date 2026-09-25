import random
from pathlib import Path

from tickterminator.detection import Box
from tickterminator.pests import Pest
from tickterminator.tiling import TilingConfig
from tickterminator.training.dataset import (
    Label,
    LabeledPhoto,
    pests_in,
    photo_tiles,
    training_tiles,
)

TILING = TilingConfig(tile_size=100, overlap=0)


def photo(*labels: Label) -> LabeledPhoto:
    return LabeledPhoto(Path("photo.jpg"), (200, 100), list(labels))


def test_label_goes_to_tile_with_its_center_in_tile_coordinates():
    tent = Label(Pest.TENT_CATERPILLAR, Box(90, 10, 130, 30))  # Center x = 110.
    left, right = photo_tiles(photo(tent), TILING)

    assert left.labels == []
    assert right.region == Box(100, 0, 200, 100)
    assert right.labels == [Label(Pest.TENT_CATERPILLAR, Box(0, 10, 30, 30))]


def test_training_tiles_balance_empty_tiles():
    tent = Label(Pest.TENT_CATERPILLAR, Box(10, 10, 20, 20))
    photos = [photo(tent), photo(), photo()]

    tiles = training_tiles(photos, TILING, random.Random(0))

    assert sum(1 for tile in tiles if tile.labels) == 1
    assert sum(1 for tile in tiles if not tile.labels) == 1


def test_pests_in_uses_enum_order():
    labels = [
        Label(Pest.DEFOLIATION, Box(0, 0, 1, 1)),
        Label(Pest.TENT_CATERPILLAR, Box(0, 0, 1, 1)),
    ]
    assert pests_in([photo(*labels)]) == [Pest.TENT_CATERPILLAR, Pest.DEFOLIATION]
