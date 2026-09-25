import pytest
from PIL import Image

from tickterminator.tiling import TilingConfig, iter_tiles, tile_starts


def test_small_image_is_one_tile():
    assert tile_starts(500, tile_size=1024, overlap=128) == [0]


def test_last_tile_ends_at_edge():
    assert tile_starts(1000, tile_size=400, overlap=100) == [0, 300, 600]


def test_tiles_cover_whole_image():
    image = Image.new("RGB", (1000, 700))
    tiles = list(iter_tiles(image, TilingConfig(tile_size=400, overlap=100)))
    assert len(tiles) == 3 * 2
    assert max(tile.x_offset + tile.image.width for tile in tiles) == 1000
    assert max(tile.y_offset + tile.image.height for tile in tiles) == 700


@pytest.mark.parametrize(("tile_size", "overlap"), [(0, 0), (100, 100), (100, -1)])
def test_invalid_config_is_rejected(tile_size, overlap):
    with pytest.raises(ValueError):
        TilingConfig(tile_size, overlap)
