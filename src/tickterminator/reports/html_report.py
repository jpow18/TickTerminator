import base64
import html
import io
import json
from dataclasses import astuple
from importlib import resources
from pathlib import Path
from string import Template

from PIL import Image

from tickterminator.detection import Box
from tickterminator.pests import Pest
from tickterminator.photos import load_image
from tickterminator.reports.rows import finding_row
from tickterminator.survey import Survey

THUMBNAIL_SIZE = 240
THUMBNAIL_CONTEXT = 0.5
"""Extra space around the box, as a fraction of the box size."""
PEST_COLORS = ("#d1495b", "#edae49", "#00798c", "#30638e", "#8c5383", "#66a182")


def write_html(survey: Survey, path: Path) -> None:
    template = Template(resources.files(__package__).joinpath("report.html").read_text())
    records = findings_with_thumbnails(survey)
    path.write_text(
        template.substitute(
            summary=html.escape(summary(survey)),
            table_rows="\n".join(table_row(record) for record in records),
            map_data=json.dumps(map_data(survey, records)).replace("</", "<\\/"),
        )
    )


def summary(survey: Survey) -> str:
    finding_count = sum(len(photo.findings) for photo in survey.photos)
    return f"{finding_count} findings in {len(survey.photos)} photos"


def findings_with_thumbnails(survey: Survey) -> list[dict]:
    records = []
    for photo in survey.photos:
        if not photo.findings:
            continue
        image = load_image(photo.path)
        for finding in photo.findings:
            record = finding_row(survey, photo, finding)
            record["thumbnail"] = thumbnail(image, finding.detection.box)
            record["color"] = pest_color(finding.detection.pest)
            records.append(record)
    return records


def thumbnail(image: Image.Image, box: Box) -> str:
    region = box.expanded(THUMBNAIL_CONTEXT).clipped(*image.size)
    crop = image.crop(astuple(region))
    crop.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
    buffer = io.BytesIO()
    crop.save(buffer, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def pest_color(pest: Pest) -> str:
    return PEST_COLORS[list(Pest).index(pest) % len(PEST_COLORS)]


def table_row(record: dict) -> str:
    cells = [
        f'<img src="{record["thumbnail"]}" alt="">',
        f'<span class="dot" style="background:{record["color"]}"></span>'
        + html.escape(record["pest"]),
        f"{record['score']:.2f}",
        html.escape(record["sector"] or "–"),
        photo_name(record["image"]),
        position_link(record),
    ]
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def photo_name(image_path: str) -> str:
    return f'<span title="{html.escape(image_path)}">{html.escape(Path(image_path).name)}</span>'


def position_link(record: dict) -> str:
    if record["latitude"] is None:
        return "–"
    latitude, longitude = record["latitude"], record["longitude"]
    url = f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=19/{latitude}/{longitude}"
    return f'<a href="{html.escape(url)}">{latitude:.6f}, {longitude:.6f}</a>'


def map_data(survey: Survey, records: list[dict]) -> dict:
    located = [record for record in records if record["latitude"] is not None]
    return {
        "findings": [
            {
                key: record[key]
                for key in (
                    "latitude",
                    "longitude",
                    "pest",
                    "score",
                    "sector",
                    "image",
                    "thumbnail",
                    "color",
                )
            }
            for record in located
        ],
        "sectors": sector_outlines(survey),
    }


def sector_outlines(survey: Survey) -> list[dict]:
    if survey.grid is None:
        return []
    outlines = {}
    for _, finding in survey.findings():
        if finding.location is None:
            continue
        north_west, south_east = survey.grid.corners(finding.location)
        outlines[survey.grid.label(finding.location)] = [
            [north_west.latitude, north_west.longitude],
            [south_east.latitude, south_east.longitude],
        ]
    return [{"label": label, "bounds": bounds} for label, bounds in outlines.items()]
