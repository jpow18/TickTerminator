import json

from conftest import save_drone_photo

from tickterminator.coco import box_from_coco, coco_bbox
from tickterminator.detection import Box
from tickterminator.pests import Pest
from tickterminator.reports import ReportFormat
from tickterminator.scan import ScanConfig, scan_folder
from tickterminator.survey import Survey
from tickterminator.training.dataset import read_coco_labels


def test_bbox_conversion_round_trips():
    box = Box(10, 20, 40, 60)
    assert coco_bbox(box) == [10, 20, 30, 40]
    assert box_from_coco(coco_bbox(box)) == box


def test_exported_pre_labels_can_be_read_as_training_labels(tmp_path, fake_detector):
    photos = tmp_path / "photos"
    (photos / "flight1").mkdir(parents=True)
    save_drone_photo(photos / "flight1" / "a.jpg")
    save_drone_photo(photos / "b.jpg")
    results = list(scan_folder(photos, fake_detector, ScanConfig(pests=list(Pest))))
    labels_file = tmp_path / "prelabels.json"

    ReportFormat.COCO.write(Survey.from_results(results), labels_file)

    document = json.loads(labels_file.read_text())
    assert [image["file_name"] for image in document["images"]] == ["b.jpg", "flight1/a.jpg"]
    labeled = read_coco_labels(labels_file, photos)
    assert labeled[1].path == photos / "flight1" / "a.jpg"
    assert labeled[1].size == (400, 300)
    assert labeled[1].labels[0].pest is Pest.TENT_CATERPILLAR
    assert labeled[1].labels[0].box == Box(0, 0, 10, 10)
