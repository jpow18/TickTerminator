"""Measure a detector against labeled photos."""

from collections.abc import Sequence
from dataclasses import dataclass

from tickterminator.detection import Detection
from tickterminator.detectors import Detector
from tickterminator.labels import Label, LabeledPhoto
from tickterminator.pests import Pest
from tickterminator.photos import load_image
from tickterminator.scan import scan_image
from tickterminator.tiling import TilingConfig

DEFAULT_IOU_THRESHOLD = 0.5


@dataclass(frozen=True)
class Counts:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    def __add__(self, other: "Counts") -> "Counts":
        return Counts(
            self.true_positives + other.true_positives,
            self.false_positives + other.false_positives,
            self.false_negatives + other.false_negatives,
        )

    @property
    def precision(self) -> float:
        found = self.true_positives + self.false_positives
        return self.true_positives / found if found else 0.0

    @property
    def recall(self) -> float:
        expected = self.true_positives + self.false_negatives
        return self.true_positives / expected if expected else 0.0

    @property
    def f1(self) -> float:
        total = self.precision + self.recall
        return 2 * self.precision * self.recall / total if total else 0.0


@dataclass(frozen=True)
class PestScore:
    pest: Pest
    min_score: float
    boxes: Counts
    """Each labeled box must be found by a detection that overlaps it."""
    photos: Counts
    """Each photo must be found to have, or not have, the pest."""


@dataclass(frozen=True)
class PhotoDetections:
    photo: LabeledPhoto
    detections: list[Detection]


def detect_all(
    photos: Sequence[LabeledPhoto],
    detector: Detector,
    pests: Sequence[Pest],
    tiling: TilingConfig,
) -> list[PhotoDetections]:
    return [
        PhotoDetections(photo, scan_image(load_image(photo.path), detector, pests, tiling))
        for photo in photos
    ]


def score(
    results: Sequence[PhotoDetections],
    pest: Pest,
    min_score: float,
    iou_threshold: float = DEFAULT_IOU_THRESHOLD,
) -> PestScore:
    boxes = photos = Counts()
    for result in results:
        detections = [
            detection
            for detection in result.detections
            if detection.pest is pest and detection.score >= min_score
        ]
        labels = [label for label in result.photo.labels if label.pest is pest]
        boxes += match_boxes(detections, labels, iou_threshold)
        photos += match_presence(bool(detections), bool(labels))
    return PestScore(pest, min_score, boxes, photos)


def best_threshold(
    results: Sequence[PhotoDetections],
    pest: Pest,
    candidates: Sequence[float],
    iou_threshold: float = DEFAULT_IOU_THRESHOLD,
) -> PestScore:
    """The candidate minimum score with the highest box F1."""
    return max(
        (score(results, pest, candidate, iou_threshold) for candidate in candidates),
        key=lambda result: result.boxes.f1,
    )


def match_boxes(
    detections: Sequence[Detection], labels: Sequence[Label], iou_threshold: float
) -> Counts:
    """Match each detection, highest score first, to the unmatched label it overlaps most."""
    unmatched = list(labels)
    true_positives = 0
    for detection in sorted(detections, key=lambda d: d.score, reverse=True):
        best = max(unmatched, key=lambda label: label.box.iou(detection.box), default=None)
        if best is not None and best.box.iou(detection.box) >= iou_threshold:
            unmatched.remove(best)
            true_positives += 1
    return Counts(true_positives, len(detections) - true_positives, len(unmatched))


def match_presence(detected: bool, labeled: bool) -> Counts:
    return Counts(
        true_positives=int(detected and labeled),
        false_positives=int(detected and not labeled),
        false_negatives=int(labeled and not detected),
    )
