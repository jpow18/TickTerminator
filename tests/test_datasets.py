import json

import pytest

from tickterminator import cli
from tickterminator.datasets import PublicDataset
from tickterminator.datasets.merge import EXPORT_ANNOTATION_FILE, Split, export_dir, merge_exports
from tickterminator.detection import Box
from tickterminator.labels import read_coco_labels
from tickterminator.pests import Pest


def save_export(output_dir, dataset, split, photos):
    """`photos` maps an original photo name to its boxes."""
    folder = export_dir(output_dir, dataset) / split.value
    folder.mkdir(parents=True)
    images, annotations = [], []
    for image_id, (name, boxes) in enumerate(photos.items()):
        file_name = f"{name}.rf.123.jpg"
        (folder / file_name).write_bytes(b"")
        images.append(
            {
                "id": image_id,
                "file_name": file_name,
                "width": 640,
                "height": 480,
                "extra": {"name": name},
            }
        )
        annotations += [
            {"id": len(annotations), "image_id": image_id, "category_id": 3, "bbox": box}
            for box in boxes
        ]
    categories = [{"id": 0, "name": "ticks"}, {"id": 3, "name": "Ixodes"}]
    document = {"images": images, "annotations": annotations, "categories": categories}
    (folder / EXPORT_ANNOTATION_FILE).write_text(json.dumps(document))


def test_merged_labels_use_the_pest_name(tmp_path):
    dataset = PublicDataset.TICK_CITIZEN_SCIENCE
    save_export(tmp_path, dataset, Split.TRAIN, {"a.jpg": [[10, 20, 30, 40]], "empty.jpg": []})

    [summary] = merge_exports(tmp_path, [dataset])

    assert (summary.split, summary.images, summary.labels) == (Split.TRAIN, 2, 1)
    photos = read_coco_labels(tmp_path / "train.json", tmp_path)
    assert photos[0].path == tmp_path / "tick_citizen_science" / "train" / "a.jpg.rf.123.jpg"
    assert photos[0].path.exists()
    assert photos[0].labels[0].pest is Pest.TICK
    assert photos[0].labels[0].box == Box(10, 20, 40, 60)
    assert photos[1].labels == []


def test_photo_in_two_datasets_stays_only_in_the_evaluation_split(tmp_path):
    save_export(tmp_path, PublicDataset.TICK_ID, Split.TRAIN, {"same.jpg": [[0, 0, 5, 5]]})
    save_export(
        tmp_path, PublicDataset.TICKS_IMAGE_DETECTION, Split.TEST, {"same.jpg": [[1, 1, 5, 5]]}
    )

    summaries = merge_exports(
        tmp_path, [PublicDataset.TICKS_IMAGE_DETECTION, PublicDataset.TICK_ID]
    )

    assert [(s.split, s.images, s.duplicates) for s in summaries] == [
        (Split.TEST, 1, 0),
        (Split.TRAIN, 0, 1),
    ]
    assert not (tmp_path / "train.json").exists()


def test_download_needs_an_api_key(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        cli.main(["download", "--pests", "tick", "--output", str(tmp_path), "--api-key", ""])
    assert "ROBOFLOW_API_KEY" in capsys.readouterr().err


def test_download_skips_datasets_that_are_already_downloaded(monkeypatch, tmp_path):
    for dataset in PublicDataset.for_pests([Pest.TICK]):
        save_export(tmp_path, dataset, Split.VALID, {f"{dataset.name}.jpg": [[0, 0, 5, 5]]})
    monkeypatch.setattr(cli, "download_coco", pytest.fail)

    cli.main(["download", "--pests", "tick", "--output", str(tmp_path), "--api-key", "key"])

    assert len(json.loads((tmp_path / "valid.json").read_text())["images"]) == 3
    assert "CC BY 4.0" in (tmp_path / "ATTRIBUTION.txt").read_text()
