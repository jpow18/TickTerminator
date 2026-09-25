import argparse
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from tickterminator.detectors import Detector, DetectorKind
from tickterminator.pests import Pest, View
from tickterminator.reports import ReportFormat
from tickterminator.scan import PhotoResult, ScanConfig, scan_folder, scan_paths
from tickterminator.survey import DEFAULT_SECTOR_SIZE_M, Survey
from tickterminator.tiling import TilingConfig
from tickterminator.watch import watch_photos

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

    pests = commands.add_parser("pests", help="List the pests the scanner can find.")
    pests.set_defaults(handler=run_pests)

    scan = commands.add_parser("scan", help="Find pests in a folder of photos.")
    scan.add_argument("folder", type=Path, help="Folder of photos. Subfolders are included.")
    add_detection_arguments(scan)
    add_report_arguments(scan)
    scan.set_defaults(handler=run_scan)

    watch = commands.add_parser(
        "watch", help="Scan new photos as they arrive in a folder. Stop with Ctrl+C."
    )
    watch.add_argument("folder", type=Path, help="Folder where new photos arrive.")
    watch.add_argument(
        "--poll-interval", type=float, default=2.0, help="Seconds between folder checks."
    )
    watch.add_argument(
        "--stop-after-idle",
        type=float,
        help="Stop when no new photos arrive for this many seconds. Default: never.",
    )
    add_detection_arguments(watch)
    add_report_arguments(watch)
    watch.set_defaults(handler=run_watch)

    train = commands.add_parser("train", help="Fine-tune a detector on labeled photos.")
    train.add_argument("labels", type=Path, help="COCO file with pest names as categories.")
    train.add_argument("--images", type=Path, required=True, help="Folder of the labeled photos.")
    train.add_argument("--output", type=Path, required=True, help="Folder for the trained model.")
    train.add_argument("--base-model", help="Hugging Face model to start from.")
    train.add_argument("--epochs", type=int)
    train.add_argument("--batch-size", type=int)
    train.add_argument("--learning-rate", type=float)
    add_tiling_arguments(train)
    train.set_defaults(handler=run_train)
    return parser


def add_detection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--pests",
        type=parse_pests,
        default=Pest.for_view(View.AERIAL),
        help="Comma-separated pests to find. Default: all pests seen from a drone.",
    )
    parser.add_argument(
        "--detector",
        type=str.upper,
        choices=[kind.name for kind in DetectorKind],
        default=DetectorKind.OWLV2.name,
        help="OWLV2 finds pests from text prompts. TRAINED uses a model from 'train'.",
    )
    parser.add_argument("--model", help="Model name or folder. Required for TRAINED.")
    parser.add_argument("--threshold", type=float, help="Minimum score, 0 to 1.")
    parser.add_argument(
        "--altitude",
        type=float,
        help="Flight height above the ground in meters. Used when photos do not record it.",
    )
    add_tiling_arguments(parser)


def add_tiling_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tile-size", type=int, default=TilingConfig.tile_size)
    parser.add_argument(
        "--overlap", type=int, help="Tile overlap in pixels. Default: tile size / 8."
    )


def add_report_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        type=Path,
        action="append",
        help="Report file. The extension sets the format: .csv, .geojson, .html, or .json "
        "(COCO pre-labels). Use more than once for more reports. "
        "Default: detections.csv and report.html.",
    )
    parser.add_argument(
        "--sector-size",
        type=float,
        default=DEFAULT_SECTOR_SIZE_M,
        help="Sector width in meters.",
    )


def run_pests(args: argparse.Namespace) -> None:
    for pest in Pest:
        print(f"{pest.name.lower():<20} {pest.spec.display_name:<26} {pest.spec.view.value}")


def run_scan(args: argparse.Namespace) -> None:
    require_folder(args.folder)
    reports = report_targets(args)
    config = scan_config(args)
    detector = create_detector(args)

    results = list(with_progress(scan_folder(args.folder, detector, config)))
    write_reports(Survey.from_results(results, args.sector_size), reports)
    warn_if_not_located(results)


def run_watch(args: argparse.Namespace) -> None:
    require_folder(args.folder)
    reports = report_targets(args)
    config = scan_config(args)
    detector = create_detector(args)
    photos = watch_photos(args.folder, args.poll_interval, args.stop_after_idle)
    print(f"Watching {args.folder}. Stop with Ctrl+C.", file=sys.stderr)

    results: list[PhotoResult] = []
    try:
        for result in with_progress(scan_paths(photos, detector, config)):
            results.append(result)
            announce_findings(result)
            if result.findings:
                write_reports(Survey.from_results(results, args.sector_size), reports)
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)
    write_reports(Survey.from_results(results, args.sector_size), reports)


def announce_findings(result: PhotoResult) -> None:
    for finding in result.findings:
        detection = finding.detection
        where = (
            f"{finding.location.latitude:.6f}, {finding.location.longitude:.6f}"
            if finding.location
            else "no position"
        )
        print(f"FOUND {detection.pest.name.lower()} ({detection.score:.2f}) at {where}")


def run_train(args: argparse.Namespace) -> None:
    from tickterminator.training.dataset import read_coco_labels
    from tickterminator.training.train import TrainingConfig, train

    require_folder(args.images)
    options = {
        "base_model": args.base_model,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
    }
    config = TrainingConfig(
        tiling=tiling_config(args),
        **{name: value for name, value in options.items() if value is not None},
    )
    photos = read_coco_labels(args.labels, args.images)
    train(photos, args.output, config, on_epoch=print_epoch)
    print(f"Model: {args.output}. Use it with: --detector trained --model {args.output}")


def print_epoch(epoch: int, loss: float) -> None:
    print(f"Epoch {epoch}: loss {loss:.4f}", file=sys.stderr)


def tiling_config(args: argparse.Namespace) -> TilingConfig:
    overlap = args.overlap if args.overlap is not None else args.tile_size // 8
    return TilingConfig(args.tile_size, overlap)


def require_folder(folder: Path) -> None:
    if not folder.is_dir():
        raise ValueError(f"Folder not found: {folder}")


def report_targets(args: argparse.Namespace) -> list[tuple[ReportFormat, Path]]:
    outputs = args.output or DEFAULT_OUTPUTS
    return [(ReportFormat.for_path(output), output) for output in outputs]


def scan_config(args: argparse.Namespace) -> ScanConfig:
    return ScanConfig(
        pests=args.pests,
        tiling=tiling_config(args),
        fallback_altitude_m=args.altitude,
    )


def create_detector(args: argparse.Namespace) -> Detector:
    return DetectorKind[args.detector].create(model=args.model, score_threshold=args.threshold)


def write_reports(survey: Survey, reports: list[tuple[ReportFormat, Path]]) -> None:
    for report_format, output in reports:
        report_format.write(survey, output)
        print(f"Report: {output}", file=sys.stderr)


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
    try:
        args.handler(args)
    except (ValueError, ImportError) as error:
        parser.error(str(error))
