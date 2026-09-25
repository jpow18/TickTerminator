from tickterminator.scan import Finding, PhotoResult
from tickterminator.survey import Survey

COLUMNS = (
    "image",
    "pest",
    "score",
    "x_min",
    "y_min",
    "x_max",
    "y_max",
    "latitude",
    "longitude",
    "sector",
)


def finding_row(survey: Survey, photo: PhotoResult, finding: Finding) -> dict:
    """One flat record per finding. All report formats use it."""
    detection = finding.detection
    box = detection.box
    location = finding.location
    return {
        "image": photo.path.as_posix(),
        "pest": detection.pest.name.lower(),
        "score": round(detection.score, 3),
        "x_min": round(box.x_min),
        "y_min": round(box.y_min),
        "x_max": round(box.x_max),
        "y_max": round(box.y_max),
        "latitude": round(location.latitude, 7) if location else None,
        "longitude": round(location.longitude, 7) if location else None,
        "sector": survey.sector(finding),
    }


def rows(survey: Survey) -> list[dict]:
    return [finding_row(survey, photo, finding) for photo, finding in survey.findings()]
