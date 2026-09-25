"""Zero-shot detector. It finds objects from text prompts, so it needs no training data."""

from collections.abc import Sequence

from PIL import Image

from tickterminator.detection import Box, Detection
from tickterminator.pests import Pest

try:
    import torch
    from transformers import Owlv2ForObjectDetection, Owlv2Processor
except ImportError as error:
    raise ImportError(
        "The OWLv2 detector needs extra packages. Install them with: "
        "pip install 'tickterminator[zero-shot]'"
    ) from error

DEFAULT_MODEL = "google/owlv2-base-patch16-ensemble"


class Owlv2Detector:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        score_threshold: float = 0.2,
        device: str | None = None,
    ) -> None:
        self._score_threshold = score_threshold
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._processor = Owlv2Processor.from_pretrained(model_name)
        self._model = Owlv2ForObjectDetection.from_pretrained(model_name).to(self._device).eval()

    def detect(self, image: Image.Image, pests: Sequence[Pest]) -> list[Detection]:
        prompt_pests = [(prompt, pest) for pest in pests for prompt in pest.spec.prompts]
        prompts = [prompt for prompt, _ in prompt_pests]

        inputs = self._processor(text=[prompts], images=image, return_tensors="pt")
        with torch.inference_mode():
            outputs = self._model(**inputs.to(self._device))

        # OWLv2 pads the image to a square at the bottom and right, so scale to the padded size.
        side = max(image.size)
        result = self._processor.image_processor.post_process_object_detection(
            outputs, threshold=self._score_threshold, target_sizes=[(side, side)]
        )[0]

        return [
            Detection(
                pest=prompt_pests[label][1],
                score=float(score),
                box=Box(*box.tolist()).clipped(*image.size),
            )
            for score, label, box in zip(
                result["scores"], result["labels"].tolist(), result["boxes"], strict=True
            )
        ]
