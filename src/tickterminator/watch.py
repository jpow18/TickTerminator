import time
from collections.abc import Callable, Iterator
from pathlib import Path

from tickterminator.photos import find_photos


class PhotoWatcher:
    """Finds new photos in a folder. A photo is ready when its size stops changing, so a
    photo that is still being copied is not read."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._done: set[Path] = set()
        self._last_sizes: dict[Path, int] = {}

    @property
    def has_pending(self) -> bool:
        return bool(self._last_sizes)

    def ready_photos(self) -> list[Path]:
        ready = []
        for path in find_photos(self._folder):
            if path in self._done:
                continue
            size = path.stat().st_size
            if size > 0 and self._last_sizes.get(path) == size:
                ready.append(path)
                self._done.add(path)
                del self._last_sizes[path]
            else:
                self._last_sizes[path] = size
        return ready


def watch_photos(
    folder: Path,
    poll_interval_s: float = 2.0,
    idle_timeout_s: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[Path]:
    """Yield each new photo once. Stop after `idle_timeout_s` with no new photos, or never."""
    watcher = PhotoWatcher(folder)
    last_activity = clock()
    while True:
        ready = watcher.ready_photos()
        yield from ready
        if ready or watcher.has_pending:
            last_activity = clock()
        elif idle_timeout_s is not None and clock() - last_activity >= idle_timeout_s:
            return
        sleep(poll_interval_s)
