"""Merge dataset exports into one COCO file for each split, with pest names as categories."""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from tickterminator import coco
from tickterminator.datasets import PublicDataset

EXPORT_ANNOTATION_FILE = "_annotations.coco.json"


class Split(Enum):
    """In this order, so a photo in more than one dataset stays in the evaluation splits and
    is removed from training."""

    TEST = "test"
    VALID = "valid"
    TRAIN = "train"

    @property
    def labels_file_name(self) -> str:
        return f"{self.value}.json"


@dataclass
class SplitSummary:
    split: Split
    images: int = 0
    labels: int = 0
    duplicates: int = 0


def export_dir(output_dir: Path, dataset: PublicDataset) -> Path:
    return output_dir / dataset.name.lower()


def merge_exports(output_dir: Path, datasets: list[PublicDataset]) -> list[SplitSummary]:
    """Read the exports in `export_dir(output_dir, dataset)` and write `<split>.json` in
    `output_dir`. Image file names are relative to `output_dir`."""
    seen_photos: set[str] = set()
    summaries = []
    for split in Split:
        summary = SplitSummary(split)
        document = {"images": [], "annotations": [], "categories": coco.categories()}
        for dataset in datasets:
            export_file = export_dir(output_dir, dataset) / split.value / EXPORT_ANNOTATION_FILE
            if export_file.exists():
                add_export(document, export_file, dataset, output_dir, seen_photos, summary)
        if document["images"]:
            (output_dir / split.labels_file_name).write_text(json.dumps(document))
        if summary.images or summary.duplicates:
            summaries.append(summary)
    return summaries


def add_export(
    document: dict,
    export_file: Path,
    dataset: PublicDataset,
    output_dir: Path,
    seen_photos: set[str],
    summary: SplitSummary,
) -> None:
    export = json.loads(export_file.read_text())
    category_id = coco.category_id(dataset.spec.pest)
    new_image_ids = {}
    for image in export["images"]:
        photo = original_name(image)
        if photo in seen_photos:
            summary.duplicates += 1
            continue
        seen_photos.add(photo)
        new_image_ids[image["id"]] = len(document["images"]) + 1
        document["images"].append(
            {
                "id": new_image_ids[image["id"]],
                "file_name": (export_file.parent / image["file_name"])
                .relative_to(output_dir)
                .as_posix(),
                "width": image["width"],
                "height": image["height"],
            }
        )
    for annotation in export["annotations"]:
        if annotation["image_id"] not in new_image_ids:
            continue
        document["annotations"].append(
            {
                "id": len(document["annotations"]) + 1,
                "image_id": new_image_ids[annotation["image_id"]],
                "category_id": category_id,
                "bbox": annotation["bbox"],
                "area": annotation["bbox"][2] * annotation["bbox"][3],
                "iscrowd": 0,
            }
        )
    summary.images = len(document["images"])
    summary.labels = len(document["annotations"])


def original_name(image: dict) -> str:
    """Roboflow renames each photo, but keeps the name of the uploaded file."""
    return image.get("extra", {}).get("name", image["file_name"])
