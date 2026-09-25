import json
from pathlib import Path

from tickterminator.reports.rows import rows
from tickterminator.survey import Survey


def write_geojson(survey: Survey, path: Path) -> None:
    """Findings with a map position, as points. Open the file in QGIS or geojson.io."""
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["longitude"], row["latitude"]]},
            "properties": row,
        }
        for row in rows(survey)
        if row["latitude"] is not None
    ]
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2))
