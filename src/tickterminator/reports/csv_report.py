import csv
from pathlib import Path

from tickterminator.reports.rows import COLUMNS, rows
from tickterminator.survey import Survey


def write_csv(survey: Survey, path: Path) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows(survey))
