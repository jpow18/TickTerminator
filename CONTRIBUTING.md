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
PINE_PROCESSIONARY = PestSpec(
    "Pine processionary moth",
    View.AERIAL,
    ("white cocoon", "white fluffy ball"),
    min_score=0.04,
)
```

- `View.AERIAL` pests are for drone photos. `View.CLOSE_UP` pests are for close-up photos, and `scan` finds them only when you name them with `--pests`.
- Write the prompts to describe what the camera sees, for example the nest, not the insect. Short, concrete phrases work better than long descriptions.
- `min_score` is the default threshold for the zero-shot detector. Good values are often much lower than 0.2.

Select the prompts and `min_score` with numbers. Label some photos (COCO format), then compare prompts with `tickterminator evaluate`. `--prompt` tests a prompt without a code change:

```bash
tickterminator evaluate labels.json --images ./photos --pests fall_webworm \
    --prompt "white web on leaves" --prompt "silk web" --thresholds 0.02,0.05,0.1,0.2
```
 See [examples/pine-processionary](examples/pine-processionary) for an example. Include the results in your pull request.

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
