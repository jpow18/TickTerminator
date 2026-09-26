"""Zero-shot detector. It finds objects from text prompts, so it needs no training data."""

from collections.abc import Mapping, Sequence

from PIL import Image

from tickterminator.detection import Box, Detection
from tickterminator.ml import default_device, torch, transformers
from tickterminator.pests import Pest

DEFAULT_MODEL = "google/owlv2-base-patch16-ensemble"


class Owlv2Detector:
    """`score_threshold` applies to all pests. When it is None, each pest uses its own
    `min_score`. `prompts` replaces the prompts of some pests, to test new prompts."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        score_threshold: float | None = None,
        prompts: Mapping[Pest, Sequence[str]] | None = None,
        device: str | None = None,
    ) -> None:
        self._score_threshold = score_threshold
        self._prompts = dict(prompts or {})
        self._device = device or default_device()
        self._processor = transformers.Owlv2Processor.from_pretrained(model)
        self._model = (
            transformers.Owlv2ForObjectDetection.from_pretrained(model).to(self._device).eval()
        )

    def detect(self, image: Image.Image, pests: Sequence[Pest]) -> list[Detection]:
        prompt_pests = [(prompt, pest) for pest in pests for prompt in self._prompts_for(pest)]
        prompts = [prompt for prompt, _ in prompt_pests]

        inputs = self._processor(text=[prompts], images=image, return_tensors="pt")
        with torch.inference_mode():
            outputs = self._model(**inputs.to(self._device))

        # OWLv2 pads the image to a square at the bottom and right, so scale to the padded size.
        side = max(image.size)
        result = self._processor.image_processor.post_process_object_detection(
            outputs, threshold=min(map(self._min_score, pests)), target_sizes=[(side, side)]
        )[0]

        detections = [
            Detection(
                pest=prompt_pests[label][1],
                score=float(score),
                box=Box(*box.tolist()).clipped(*image.size),
            )
            for score, label, box in zip(
                result["scores"], result["labels"].tolist(), result["boxes"], strict=True
            )
        ]
        return [
            detection
            for detection in detections
            if detection.score >= self._min_score(detection.pest)
        ]

    def _prompts_for(self, pest: Pest) -> Sequence[str]:
        return self._prompts.get(pest, pest.spec.prompts)

    def _min_score(self, pest: Pest) -> float:
        return self._score_threshold if self._score_threshold is not None else pest.spec.min_score
