from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class PestSpec:
    display_name: str
    prompts: tuple[str, ...]
    """Text prompts for zero-shot detectors. Describe what a drone camera sees."""


class Pest(Enum):
    """Pests the scanner can find. To add a pest, add a member here."""

    TENT_CATERPILLAR = PestSpec(
        "Eastern tent caterpillar",
        ("silk web tent in the fork of tree branches", "white silk caterpillar nest in a tree"),
    )
    FALL_WEBWORM = PestSpec(
        "Fall webworm",
        ("silk web covering the leaves at the end of a tree branch",),
    )
    DEFOLIATION = PestSpec(
        "Defoliation",
        ("bare leafless tree crown among green trees",),
    )

    @property
    def spec(self) -> PestSpec:
        return self.value

    @classmethod
    def parse(cls, name: str) -> "Pest":
        try:
            return cls[name.strip().upper()]
        except KeyError:
            choices = ", ".join(pest.name.lower() for pest in cls)
            raise ValueError(f"Unknown pest '{name}'. Choices: {choices}") from None
