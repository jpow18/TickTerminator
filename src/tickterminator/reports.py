import csv
from collections.abc import Callable, Iterable
from enum import Enum
from pathlib import Path

from tickterminator.scan import ImageResult

CSV_COLUMNS = ("image", "pest", "score", "x_min", "y_min", "x_max", "y_max")


def write_csv(results: Iterable[ImageResult], path: Path) -> None:
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_COLUMNS)
        for result in results:
            for detection in result.detections:
                box = detection.box
                writer.writerow(
                    (
                        result.image_path.as_posix(),
                        detection.pest.name.lower(),
                        f"{detection.score:.3f}",
                        *(round(value) for value in (box.x_min, box.y_min, box.x_max, box.y_max)),
                    )
                )


ReportWriter = Callable[[Iterable[ImageResult], Path], None]

_WRITERS: dict[str, ReportWriter] = {"csv": write_csv}


class ReportFormat(Enum):
    """Output formats. To add a format, add a member and a writer in `_WRITERS`."""

    CSV = "csv"

    def write(self, results: Iterable[ImageResult], path: Path) -> None:
        _WRITERS[self.value](results, path)
