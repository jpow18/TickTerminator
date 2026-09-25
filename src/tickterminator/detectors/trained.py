"""Detector for a model made with `tickterminator train`, or any Hugging Face object detection model
with pest names as labels."""

from collections.abc import Sequence

from PIL import Image

from tickterminator.detection import Box, Detection
from tickterminator.ml import default_device, torch, transformers
from tickterminator.pests import Pest


class TrainedDetector:
    def __init__(
        self,
        model: str | None = None,
        score_threshold: float = 0.5,
        device: str | None = None,
    ) -> None:
        if model is None:
            raise ValueError("The trained detector needs a model folder (--model).")
        self._score_threshold = score_threshold
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
            outputs, threshold=self._score_threshold, target_sizes=[(height, width)]
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
        return [detection for detection in detections if detection.pest in pests]
