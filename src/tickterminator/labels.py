"""Labeled photos: the ground truth for training and evaluation."""

import json
from dataclasses import dataclass
from pathlib import Path

from tickterminator.coco import box_from_coco
from tickterminator.detection import Box
from tickterminator.pests import Pest


@dataclass(frozen=True)
class Label:
    pest: Pest
    box: Box


@dataclass(frozen=True)
class LabeledPhoto:
    path: Path
    size: tuple[int, int]
    labels: list[Label]


def read_coco_labels(annotation_file: Path, images_dir: Path) -> list[LabeledPhoto]:
    """Read a COCO file. Category names must be pest names, for example "tent_caterpillar"."""
    document = json.loads(annotation_file.read_text())
    pests = {category["id"]: Pest.parse(category["name"]) for category in document["categories"]}
    labels_by_image: dict[int, list[Label]] = {image["id"]: [] for image in document["images"]}
    for annotation in document["annotations"]:
        labels_by_image[annotation["image_id"]].append(
            Label(pests[annotation["category_id"]], box_from_coco(annotation["bbox"]))
        )
    return [
        LabeledPhoto(
            images_dir / image["file_name"],
            (image["width"], image["height"]),
            labels_by_image[image["id"]],
        )
        for image in document["images"]
    ]


def pests_in(photos: list[LabeledPhoto]) -> list[Pest]:
    found = {label.pest for photo in photos for label in photo.labels}
    return [pest for pest in Pest if pest in found]
