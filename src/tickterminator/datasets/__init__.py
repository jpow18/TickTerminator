"""Public labeled datasets to train and evaluate detectors."""

from dataclasses import dataclass
from enum import Enum

from tickterminator.pests import Pest


@dataclass(frozen=True)
class DatasetSpec:
    workspace: str
    project: str
    version: int
    license: str
    pest: Pest
    """All categories of the dataset become this pest, for example tick species become "tick"."""

    @property
    def url(self) -> str:
        return (
            f"https://universe.roboflow.com/{self.workspace}/{self.project}/dataset/{self.version}"
        )


class PublicDataset(Enum):
    """Roboflow Universe datasets. To add a dataset, add a member here. Use a version without
    augmentation: augmented copies of one photo in different splits make evaluation too good."""

    TICKS_IMAGE_DETECTION = DatasetSpec(
        "ticks-gftpi", "ticks-image-detection", 5, "Public Domain", Pest.TICK
    )
    TICK_CITIZEN_SCIENCE = DatasetSpec(
        "tickcitizenscience", "tick-qk4y9", 1, "CC BY 4.0", Pest.TICK
    )
    TICK_ID = DatasetSpec("christopher-9mqni", "tick-id-kdclh", 2, "CC BY 4.0", Pest.TICK)

    @property
    def spec(self) -> DatasetSpec:
        return self.value

    @property
    def attribution(self) -> str:
        spec = self.spec
        return f"{spec.workspace}/{spec.project} v{spec.version}, {spec.license}: {spec.url}"

    @classmethod
    def for_pests(cls, pests: list[Pest]) -> list["PublicDataset"]:
        return [dataset for dataset in cls if dataset.spec.pest in pests]
