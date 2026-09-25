import json
import os
from pathlib import Path

from tickterminator import coco
from tickterminator.survey import Survey


def write_coco(survey: Survey, path: Path) -> None:
    """Findings as pre-labels. Correct them in CVAT or Label Studio, then use them to train a model.

    File names are relative to the folder that contains all photos.
    """
    root = photo_root(survey)
    images, annotations = [], []
    for image_id, photo in enumerate(survey.photos, start=1):
        width, height = photo.size
        images.append(
            {
                "id": image_id,
                "file_name": photo.path.relative_to(root).as_posix(),
                "width": width,
                "height": height,
            }
        )
        for finding in photo.findings:
            box = finding.detection.box
            annotations.append(
                {
                    "id": len(annotations) + 1,
                    "image_id": image_id,
                    "category_id": coco.category_id(finding.detection.pest),
                    "bbox": [round(value, 1) for value in coco.coco_bbox(box)],
                    "area": round(box.area, 1),
                    "iscrowd": 0,
                    "score": round(finding.detection.score, 3),
                }
            )
    document = {"images": images, "annotations": annotations, "categories": coco.categories()}
    path.write_text(json.dumps(document, indent=2))


def photo_root(survey: Survey) -> Path:
    if not survey.photos:
        return Path()
    return Path(os.path.commonpath([photo.path.parent for photo in survey.photos]))
