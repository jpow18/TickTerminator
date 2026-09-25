import argparse
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

from tickterminator.detectors import DetectorKind
from tickterminator.pests import Pest
from tickterminator.reports import ReportFormat
from tickterminator.scan import ImageResult, scan_folder
from tickterminator.tiling import TilingConfig


def parse_pests(value: str) -> list[Pest]:
    try:
        return [Pest.parse(name) for name in value.split(",") if name.strip()]
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def parse_report_format(output: Path) -> ReportFormat:
    try:
        return ReportFormat(output.suffix.lstrip(".").lower())
    except ValueError:
        choices = ", ".join(f".{report_format.value}" for report_format in ReportFormat)
        raise ValueError(f"Unknown output type '{output}'. Use: {choices}") from None


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
    scan.add_argument("--output", type=Path, default=Path("detections.csv"))
    scan.add_argument(
        "--detector",
        type=str.upper,
        choices=[kind.name for kind in DetectorKind],
        default=DetectorKind.OWLV2.name,
    )
    scan.add_argument("--threshold", type=float, default=0.2, help="Minimum score, 0 to 1.")
    scan.add_argument("--tile-size", type=int, default=TilingConfig.tile_size)
    scan.add_argument("--overlap", type=int, default=TilingConfig.overlap)
    return parser


def list_pests() -> None:
    for pest in Pest:
        print(f"{pest.name.lower():<20} {pest.spec.display_name}")


def scan(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not args.folder.is_dir():
        parser.error(f"Folder not found: {args.folder}")
    try:
        report_format = parse_report_format(args.output)
        tiling = TilingConfig(args.tile_size, args.overlap)
        detector = DetectorKind[args.detector].create(score_threshold=args.threshold)
    except (ValueError, ImportError) as error:
        parser.error(str(error))

    results = scan_folder(args.folder, detector, args.pests, tiling)
    report_format.write(with_progress(results), args.output)
    print(f"Report: {args.output}", file=sys.stderr)


def with_progress(results: Iterator[ImageResult]) -> Iterator[ImageResult]:
    for result in results:
        print(f"{result.image_path}: {len(result.detections)} detections", file=sys.stderr)
        yield result


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "pests":
        list_pests()
    elif args.command == "scan":
        scan(args, parser)
