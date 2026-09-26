"""Detector for a model made with `tickterminator train`, or any Hugging Face object detection model
with pest names as labels."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from PIL import Image

from tickterminator.detection import Box, Detection
from tickterminator.ml import default_device, torch, transformers
from tickterminator.pests import Pest

THRESHOLDS_FILE = "thresholds.json"
DEFAULT_SCORE_THRESHOLD = 0.5


def save_thresholds(model_dir: Path, thresholds: Mapping[Pest, float]) -> None:
    document = {pest.name.lower(): threshold for pest, threshold in thresholds.items()}
    (model_dir / THRESHOLDS_FILE).write_text(json.dumps(document, indent=2))


def load_thresholds(model_dir: Path) -> dict[Pest, float]:
    path = model_dir / THRESHOLDS_FILE
    if not path.exists():
        return {}
    return {Pest.parse(name): value for name, value in json.loads(path.read_text()).items()}


class TrainedDetector:
    """`score_threshold` applies to all pests. When it is None, each pest uses the threshold
    that `tickterminator train --validation` saved with the model, or 0.5."""

    def __init__(
        self,
        model: str | None = None,
        score_threshold: float | None = None,
        device: str | None = None,
    ) -> None:
        if model is None:
            raise ValueError("The trained detector needs a model folder (--model).")
        self._score_threshold = score_threshold
        self._saved_thresholds = load_thresholds(Path(model))
        self._device = device or default_device()
        self._processor = transformers.AutoImageProcessor.from_pretrained(model)
        self._model = (
            transformers.AutoModelForObjectDetection.from_pretrained(model).to(self._device).eval()
        )
        self._label_pests = {
            int(label): Pest.parse(name) for label, name in self._model.config.id2label.items()
        }

    def detect(self, image: Image.Image, pests: Sequence[Pest]) -> list[Detection]:
        inputs = self._processor(images=image, return_tensors="pt")
        with torch.inference_mode():
            outputs = self._model(**inputs.to(self._device))
        width, height = image.size
        result = self._processor.post_process_object_detection(
            outputs,
            threshold=min(
                (self._threshold(pest) for pest in pests), default=DEFAULT_SCORE_THRESHOLD
            ),
            target_sizes=[(height, width)],
        )[0]

        detections = [
            Detection(
                pest=self._label_pests[label],
                score=float(score),
                box=Box(*box.tolist()).clipped(width, height),
            )
            for score, label, box in zip(
                result["scores"], result["labels"].tolist(), result["boxes"], strict=True
            )
        ]
        return [
            detection
            for detection in detections
            if detection.pest in pests and detection.score >= self._threshold(detection.pest)
        ]

    def _threshold(self, pest: Pest) -> float:
        if self._score_threshold is not None:
            return self._score_threshold
        return self._saved_thresholds.get(pest, DEFAULT_SCORE_THRESHOLD)
