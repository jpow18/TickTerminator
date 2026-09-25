# Contributing

## Set up

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync
uv run pytest
uv run ruff format .
uv run ruff check .
```

The tests use a fake detector, so you do not need PyTorch to run them. To run real scans and training, also install the extra: `uv sync --extra ml`.

## Add a pest

Add a member to `Pest` in `src/tickterminator/pests.py`:

```python
BAGWORM = PestSpec(
    "Bagworm",
    ("small brown cone-shaped silk bags hanging from evergreen branches",),
)
```

Write the prompts to describe what a drone camera sees, not the insect itself. Test the prompts on real drone photos, and include example results in your pull request.

## Add a detector

1. Write a class with a `detect(image, pests)` method that returns a list of `Detection` objects. See the `Detector` protocol in `src/tickterminator/detectors/__init__.py`.
2. Add a member to `DetectorKind` with the import path of your class.
3. Import heavy dependencies from `tickterminator.ml`, so a missing extra gives a clear error.

## Add a report format

Write a writer function in a new module in `src/tickterminator/reports/`, then add a member to `ReportFormat` with the file extension and the writer.

## Code style

- Clear names are better than comments.
- Keep modules small and focused.
- Add tests for new behavior.
