import argparse
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from tickterminator.detectors import Detector, DetectorKind
from tickterminator.evaluation import DEFAULT_IOU_THRESHOLD, PestScore, detect_all, score
from tickterminator.labels import pests_in, read_coco_labels
from tickterminator.pests import Pest, View
from tickterminator.planning import (
    DEFAULT_OVERLAP,
    DEFAULT_PIXELS_ACROSS,
    MAX_LEGAL_ALTITUDE_M,
    Camera,
    CameraModel,
    plan_flight,
)
from tickterminator.reports import ReportFormat
from tickterminator.scan import PhotoResult, ScanConfig, scan_folder, scan_paths
from tickterminator.survey import DEFAULT_SECTOR_SIZE_M, Survey
from tickterminator.tiling import TilingConfig
from tickterminator.watch import watch_photos

DEFAULT_OUTPUTS = [Path("detections.csv"), Path("report.html")]
DEFAULT_EVALUATION_THRESHOLDS = [0.1, 0.2, 0.3, 0.5]


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

    evaluate = commands.add_parser(
        "evaluate", help="Measure a detector against labeled photos (a COCO file)."
    )
    evaluate.add_argument("labels", type=Path, help="COCO file with pest names as categories.")
    evaluate.add_argument("--images", type=Path, required=True, help="Folder of the photos.")
    add_detector_arguments(evaluate, default_pests=None)
    evaluate.add_argument(
        "--thresholds",
        type=parse_thresholds,
        default=DEFAULT_EVALUATION_THRESHOLDS,
        help="Comma-separated minimum scores to compare. Default: 0.1,0.2,0.3,0.5.",
    )
    evaluate.add_argument(
        "--iou",
        type=float,
        default=DEFAULT_IOU_THRESHOLD,
        help="Minimum overlap (IoU) between a detection and a label to count as found.",
    )
    evaluate.set_defaults(handler=run_evaluate)

    plan = commands.add_parser("plan", help="Calculate how high to fly for a survey.")
    plan.add_argument(
        "--target-cm", type=float, required=True, help="Smallest target to find, in cm."
    )
    plan.add_argument("--camera", type=str.upper, choices=[model.name for model in CameraModel])
    plan.add_argument(
        "--focal-length", type=float, help="35 mm equivalent focal length, for other cameras."
    )
    plan.add_argument(
        "--image-size", type=parse_image_size, help="WIDTHxHEIGHT in pixels, for other cameras."
    )
    plan.add_argument(
        "--pixels-across",
        type=int,
        default=DEFAULT_PIXELS_ACROSS,
        help="Pixels across the smallest target. More pixels give better detection.",
    )
    plan.add_argument(
        "--photo-overlap",
        type=float,
        default=DEFAULT_OVERLAP,
        help="Overlap between neighboring photos, 0 to 1.",
    )
    plan.set_defaults(handler=run_plan)

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
    add_detector_arguments(parser, default_pests=Pest.for_view(View.AERIAL))
    parser.add_argument("--threshold", type=float, help="Minimum score, 0 to 1.")
    parser.add_argument(
        "--altitude",
        type=float,
        help="Flight height above the ground in meters. Used when photos do not record it.",
    )


def add_detector_arguments(
    parser: argparse.ArgumentParser, default_pests: list[Pest] | None
) -> None:
    parser.add_argument(
        "--pests",
        type=parse_pests,
        default=default_pests,
        help="Comma-separated pests to find. "
        + (
            "Default: all pests seen from a drone."
            if default_pests
            else "Default: the pests in the labels."
        ),
    )
    parser.add_argument(
        "--detector",
        type=str.upper,
        choices=[kind.name for kind in DetectorKind],
        default=DetectorKind.OWLV2.name,
        help="OWLV2 finds pests from text prompts. TRAINED uses a model from 'train'.",
    )
    parser.add_argument("--model", help="Model name or folder. Required for TRAINED.")
    parser.add_argument(
        "--prompt",
        action="append",
        help="Test a prompt for OWLV2: replaces the prompts of the one pest in --pests. "
        "Use more than once for more prompts.",
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
    detector = create_detector(args, args.threshold, args.pests)

    results = list(with_progress(scan_folder(args.folder, detector, config)))
    write_reports(Survey.from_results(results, args.sector_size), reports)
    warn_if_not_located(results)


def run_watch(args: argparse.Namespace) -> None:
    require_folder(args.folder)
    reports = report_targets(args)
    config = scan_config(args)
    detector = create_detector(args, args.threshold, args.pests)
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


def run_evaluate(args: argparse.Namespace) -> None:
    require_folder(args.images)
    photos = read_coco_labels(args.labels, args.images)
    pests = args.pests or pests_in(photos)
    detector = create_detector(args, min(args.thresholds), pests)
    results = detect_all(photos, detector, pests, tiling_config(args))
    print(f"{len(photos)} photos, {sum(len(photo.labels) for photo in photos)} labels")
    print(SCORE_HEADER)
    for pest in pests:
        for threshold in args.thresholds:
            print(format_score(score(results, pest, threshold, args.iou)))


SCORE_HEADER = (
    f"{'pest':<20} {'threshold':>9} {'labels':>6} {'found':>5} {'correct':>7} "
    f"{'precision':>9} {'recall':>6} {'f1':>5} {'photo f1':>8}"
)


def format_score(result: PestScore) -> str:
    boxes = result.boxes
    return (
        f"{result.pest.name.lower():<20} {result.min_score:>9.2f} "
        f"{boxes.true_positives + boxes.false_negatives:>6} "
        f"{boxes.true_positives + boxes.false_positives:>5} {boxes.true_positives:>7} "
        f"{boxes.precision:>9.2f} {boxes.recall:>6.2f} {boxes.f1:>5.2f} "
        f"{result.photos.f1:>8.2f}"
    )


def parse_thresholds(value: str) -> list[float]:
    try:
        thresholds = [float(part) for part in value.split(",") if part.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a list of numbers: '{value}'") from None
    if not thresholds:
        raise argparse.ArgumentTypeError("Give at least one threshold.")
    return thresholds


def run_plan(args: argparse.Namespace) -> None:
    flight = plan_flight(
        selected_camera(args), args.target_cm / 100, args.pixels_across, args.photo_overlap
    )
    camera = flight.camera
    width_m, height_m = flight.footprint_m
    print(
        f"Camera: {camera.name} ({camera.focal_length_35mm:g} mm, "
        f"{camera.width_px} x {camera.height_px} pixels)"
    )
    print(f"Fly at most {flight.altitude_m:.0f} m above the tree tops.")
    print(
        f"Ground resolution: {flight.meters_per_pixel * 100:.2f} cm per pixel. "
        f"A {args.target_cm:g} cm target is {args.pixels_across} pixels wide."
    )
    print(f"Each photo covers {width_m:.0f} x {height_m:.0f} m.")
    print(
        f"With {args.photo_overlap:.0%} overlap: take a photo every "
        f"{flight.photo_spacing_m:.1f} m, and fly lines {flight.line_spacing_m:.1f} m apart."
    )
    if flight.exceeds_legal_altitude:
        print(
            f"Warning: the limit for small drones is usually {MAX_LEGAL_ALTITUDE_M:.0f} m. "
            "Fly lower."
        )


def selected_camera(args: argparse.Namespace) -> Camera:
    if args.camera:
        return CameraModel[args.camera].camera
    if args.focal_length and args.image_size:
        return Camera("custom camera", args.focal_length, *args.image_size)
    raise ValueError("Give --camera, or --focal-length and --image-size.")


def parse_image_size(value: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in value.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Use WIDTHxHEIGHT, for example 5472x3648: '{value}'"
        ) from None
    return width, height


def run_train(args: argparse.Namespace) -> None:
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


def create_detector(
    args: argparse.Namespace, score_threshold: float | None, pests: Sequence[Pest]
) -> Detector:
    return DetectorKind[args.detector].create(
        model=args.model,
        score_threshold=score_threshold,
        prompts=prompt_override(args, pests),
    )


def prompt_override(args: argparse.Namespace, pests: Sequence[Pest]) -> dict | None:
    if not args.prompt:
        return None
    if DetectorKind[args.detector] is not DetectorKind.OWLV2:
        raise ValueError("--prompt works only with the OWLV2 detector.")
    if len(pests) != 1:
        raise ValueError("--prompt needs exactly one pest in --pests.")
    return {pests[0]: tuple(args.prompt)}


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
