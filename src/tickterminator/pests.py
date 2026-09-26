from dataclasses import dataclass
from enum import Enum


class View(Enum):
    AERIAL = "drone photo from above"
    CLOSE_UP = "close-up photo, for example from a phone"


@dataclass(frozen=True)
class PestSpec:
    display_name: str
    view: View
    prompts: tuple[str, ...]
    """Text prompts for zero-shot detectors. Describe what the camera sees."""


class Pest(Enum):
    """Pests the scanner can find. To add a pest, add a member here."""

    TENT_CATERPILLAR = PestSpec(
        "Eastern tent caterpillar",
        View.AERIAL,
        ("silk web tent in the fork of tree branches", "white silk caterpillar nest in a tree"),
    )
    FALL_WEBWORM = PestSpec(
        "Fall webworm",
        View.AERIAL,
        ("silk web covering the leaves at the end of a tree branch",),
    )
    BAGWORM = PestSpec(
        "Bagworm",
        View.AERIAL,
        ("brown cone-shaped bags hanging from evergreen branches", "brown dead patch on a conifer"),
    )
    PINE_PROCESSIONARY = PestSpec(
        "Pine processionary moth",
        View.AERIAL,
        ("white silk nest at the tip of a pine branch", "silk caterpillar nest in a pine tree"),
    )
    DEFOLIATION = PestSpec(
        "Defoliation",
        View.AERIAL,
        ("bare leafless tree crown among green trees",),
    )
    TICK = PestSpec(
        "Tick",
        View.CLOSE_UP,
        ("small dark brown tick on white cloth", "tick in animal fur"),
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

    @classmethod
    def for_view(cls, view: View) -> list["Pest"]:
        return [pest for pest in cls if pest.spec.view is view]
