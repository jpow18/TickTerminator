"""COCO object detection format. CVAT, Label Studio and most training tools use it."""

from tickterminator.detection import Box
from tickterminator.pests import Pest


def category_id(pest: Pest) -> int:
    return list(Pest).index(pest) + 1


def categories() -> list[dict]:
    return [{"id": category_id(pest), "name": pest.name.lower()} for pest in Pest]


def coco_bbox(box: Box) -> list[float]:
    """COCO boxes are [x, y, width, height]."""
    return [box.x_min, box.y_min, box.x_max - box.x_min, box.y_max - box.y_min]


def box_from_coco(bbox: list[float]) -> Box:
    x, y, width, height = bbox
    return Box(x, y, x + width, y + height)
