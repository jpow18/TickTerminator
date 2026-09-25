from collections.abc import Sequence

import pytest
from PIL import Image

from tickterminator.detection import Box, Detection
from tickterminator.pests import Pest


class FakeDetector:
    """Finds one tent in the top-left corner of every image it gets."""

    def __init__(self, score_threshold: float = 0.2) -> None:
        self.score_threshold = score_threshold
        self.image_sizes: list[tuple[int, int]] = []

    def detect(self, image: Image.Image, pests: Sequence[Pest]) -> list[Detection]:
        self.image_sizes.append(image.size)
        return [Detection(Pest.TENT_CATERPILLAR, 0.9, Box(0, 0, 10, 10))]


@pytest.fixture
def fake_detector() -> FakeDetector:
    return FakeDetector()
