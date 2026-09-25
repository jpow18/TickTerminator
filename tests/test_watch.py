from PIL import Image

from tickterminator import cli
from tickterminator.detectors import DetectorKind
from tickterminator.watch import PhotoWatcher, watch_photos


def test_photo_is_ready_when_size_is_stable(tmp_path):
    watcher = PhotoWatcher(tmp_path)
    Image.new("RGB", (8, 8)).save(tmp_path / "a.jpg")

    assert watcher.ready_photos() == []
    assert watcher.has_pending
    assert watcher.ready_photos() == [tmp_path / "a.jpg"]
    assert watcher.ready_photos() == []


def test_growing_photo_is_not_ready(tmp_path):
    watcher = PhotoWatcher(tmp_path)
    photo = tmp_path / "a.jpg"
    photo.write_bytes(b"part")
    watcher.ready_photos()
    photo.write_bytes(b"part and more")

    assert watcher.ready_photos() == []


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_watch_yields_new_photos_then_stops_when_idle(tmp_path):
    clock = FakeClock()
    Image.new("RGB", (8, 8)).save(tmp_path / "a.jpg")

    photos = watch_photos(
        tmp_path, poll_interval_s=1, idle_timeout_s=5, clock=clock, sleep=clock.sleep
    )

    assert next(photos) == tmp_path / "a.jpg"
    Image.new("RGB", (8, 8)).save(tmp_path / "b.jpg")
    assert list(photos) == [tmp_path / "b.jpg"]
    assert clock.now >= 5


def test_watch_command_writes_reports(tmp_path, monkeypatch, fake_detector, capsys):
    monkeypatch.setattr(DetectorKind, "create", lambda self, **options: fake_detector)
    photos = tmp_path / "photos"
    photos.mkdir()
    Image.new("RGB", (64, 64)).save(photos / "a.jpg")
    report = tmp_path / "live.csv"

    cli.main(
        ["watch", str(photos), "--poll-interval", "0.01", "--stop-after-idle", "0.05",
         "--output", str(report)]
    )  # fmt: skip

    assert "FOUND tent_caterpillar (0.90) at no position" in capsys.readouterr().out
    assert "a.jpg" in report.read_text()
