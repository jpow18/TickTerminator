import argparse
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from tickterminator.detectors import DetectorKind
from tickterminator.pests import Pest
from tickterminator.reports import ReportFormat
from tickterminator.scan import PhotoResult, ScanConfig, scan_folder
from tickterminator.survey import DEFAULT_SECTOR_SIZE_M, Survey
from tickterminator.tiling import TilingConfig

DEFAULT_OUTPUTS = [Path("detections.csv"), Path("report.html")]


def parse_pests(value: str) -> list[Pest]:
    try:
        return [Pest.parse(name) for name in value.split(",") if name.strip()]
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tickterminator", description="Find pests in drone photos."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("pests", help="List the pests the scanner can find.")

    scan = commands.add_parser("scan", help="Find pests in a folder of photos.")
    scan.add_argument("folder", type=Path, help="Folder of photos. Subfolders are included.")
    scan.add_argument(
        "--pests",
        type=parse_pests,
        default=list(Pest),
        help="Comma-separated pests to find. Default: all.",
    )
    scan.add_argument(
        "--output",
        type=Path,
        action="append",
        help="Report file. The extension sets the format: .csv, .geojson or .html. "
        "Use more than once for more reports. Default: detections.csv and report.html.",
    )
    scan.add_argument(
        "--detector",
        type=str.upper,
        choices=[kind.name for kind in DetectorKind],
        default=DetectorKind.OWLV2.name,
    )
    scan.add_argument("--threshold", type=float, default=0.2, help="Minimum score, 0 to 1.")
    scan.add_argument("--tile-size", type=int, default=TilingConfig.tile_size)
    scan.add_argument("--overlap", type=int, default=TilingConfig.overlap)
    scan.add_argument(
        "--altitude",
        type=float,
        help="Flight height above the ground in meters. Used when photos do not record it.",
    )
    scan.add_argument(
        "--sector-size",
        type=float,
        default=DEFAULT_SECTOR_SIZE_M,
        help="Sector width in meters.",
    )
    return parser


def list_pests() -> None:
    for pest in Pest:
        print(f"{pest.name.lower():<20} {pest.spec.display_name}")


def scan(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not args.folder.is_dir():
        parser.error(f"Folder not found: {args.folder}")
    outputs = args.output or DEFAULT_OUTPUTS
    try:
        report_formats = [ReportFormat.for_path(output) for output in outputs]
        config = ScanConfig(
            pests=args.pests,
            tiling=TilingConfig(args.tile_size, args.overlap),
            fallback_altitude_m=args.altitude,
        )
        detector = DetectorKind[args.detector].create(score_threshold=args.threshold)
    except (ValueError, ImportError) as error:
        parser.error(str(error))

    results = list(with_progress(scan_folder(args.folder, detector, config)))
    survey = Survey.from_results(results, args.sector_size)
    for report_format, output in zip(report_formats, outputs, strict=True):
        report_format.write(survey, output)
        print(f"Report: {output}", file=sys.stderr)
    warn_if_not_located(results)


def with_progress(results: Iterable[PhotoResult]) -> Iterator[PhotoResult]:
    for result in results:
        print(f"{result.path}: {len(result.findings)} findings", file=sys.stderr)
        yield result


def warn_if_not_located(results: Sequence[PhotoResult]) -> None:
    missing = sum(1 for result in results if result.pose is None)
    if missing:
        print(
            f"Note: {missing} photos have no usable position data (GPS, altitude, "
            "35 mm focal length, camera pointing down). Their findings are not on the map. "
            "If the photos do not record altitude, use --altitude.",
            file=sys.stderr,
        )


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "pests":
        list_pests()
    elif args.command == "scan":
        scan(args, parser)
