from collections.abc import Sequence
from enum import Enum
from importlib import import_module
from typing import Any, Protocol

from PIL import Image

from tickterminator.detection import Detection
from tickterminator.pests import Pest


class Detector(Protocol):
    def detect(self, image: Image.Image, pests: Sequence[Pest]) -> list[Detection]:
        """Return detections in the pixel coordinates of `image`."""
        ...


class DetectorKind(Enum):
    """Available detectors. The value is the import path, so heavy dependencies load lazily."""

    OWLV2 = "tickterminator.detectors.owlv2:Owlv2Detector"

    def create(self, **options: Any) -> Detector:
        module_name, class_name = self.value.split(":")
        detector_class = getattr(import_module(module_name), class_name)
        return detector_class(**options)
