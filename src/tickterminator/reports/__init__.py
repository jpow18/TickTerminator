from collections.abc import Callable
from enum import Enum
from pathlib import Path

from tickterminator.reports.coco_report import write_coco
from tickterminator.reports.csv_report import write_csv
from tickterminator.reports.geojson_report import write_geojson
from tickterminator.reports.html_report import write_html
from tickterminator.survey import Survey

ReportWriter = Callable[[Survey, Path], None]


class ReportFormat(Enum):
    """Output formats, by file extension. To add a format, add a member and its writer."""

    CSV = ("csv", write_csv)
    GEOJSON = ("geojson", write_geojson)
    HTML = ("html", write_html)
    COCO = ("json", write_coco)

    def __init__(self, extension: str, writer: ReportWriter) -> None:
        self.extension = extension
        self.writer = writer

    @classmethod
    def for_path(cls, path: Path) -> "ReportFormat":
        extension = path.suffix.lstrip(".").lower()
        for report_format in cls:
            if report_format.extension == extension:
                return report_format
        choices = ", ".join(f".{report_format.extension}" for report_format in cls)
        raise ValueError(f"Unknown output type '{path}'. Use: {choices}")

    def write(self, survey: Survey, path: Path) -> None:
        self.writer(survey, path)
