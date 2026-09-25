# TickTerminator

Find pests in drone photos.

Fly a drone over a forest, orchard or nursery. Give the photos to TickTerminator. It tells you which photos show pests, and where in each photo.

The first target is the **eastern tent caterpillar**. Its silk tents are large and easy to see from the air. Ticks are too small for a drone camera, so they are a future target for a different camera setup.

> **Status:** early prototype. The detector is zero-shot: it finds pests from text descriptions and needs no training data. Results will have errors. Always check a detection before you act on it.

## Install

Requires Python 3.10 or later.

```bash
git clone https://github.com/jpow18/TickTerminator.git
cd TickTerminator
pip install '.[zero-shot]'
```

The `zero-shot` extra installs PyTorch and Hugging Face Transformers. The first scan downloads the OWLv2 model (about 600 MB).

## Use

```bash
tickterminator pests                     # list the pests you can find
tickterminator scan ./flight_photos      # find all pests, write detections.csv and report.html
tickterminator scan ./flight_photos --pests tent_caterpillar --threshold 0.3 --output tents.geojson
```

### Reports

The file extension of `--output` sets the format. Use `--output` more than once to get more reports.

| Format | Contents |
|---|---|
| `.html` | Map with a marker for each finding, sector outlines, and a table with a close-up photo of each finding. Open it in a web browser. |
| `.csv` | One row for each finding. Open it in a spreadsheet. |
| `.geojson` | Findings as map points. Open it in QGIS, Google Earth Pro or geojson.io. |

Example CSV row:

| image | pest | score | x_min | y_min | x_max | y_max | latitude | longitude | sector |
|---|---|---|---|---|---|---|---|---|---|
| flight_photos/DJI_0042.JPG | tent_caterpillar | 0.412 | 2210 | 1305 | 2398 | 1466 | 45.5000316 | -73.2500416 | 7B |

Box coordinates are pixels from the top-left corner of the photo.

### Map positions and sectors

TickTerminator calculates the ground position of each finding from the photo metadata:

- GPS position (EXIF)
- 35 mm equivalent focal length (EXIF)
- Height above the ground, and gimbal angles (DJI XMP metadata)

The camera must point straight down (within 10°). If your drone does not record the height above the ground, give it with `--altitude`. The calculation assumes flat ground, so expect an error of a few meters.

The flight area is divided into square sectors (default 50 m, set with `--sector-size`). Columns are numbers from west to east. Rows are letters from north to south. "Sector 7B" is the seventh column and the second row.

### Options

| Option | Default | Description |
|---|---|---|
| `--pests` | all | Comma-separated pest names. |
| `--threshold` | 0.2 | Minimum score, 0 to 1. Increase it to get fewer false detections. |
| `--output` | `detections.csv`, `report.html` | Report file. Use more than once. |
| `--altitude` | from photo | Flight height above the ground, in meters. |
| `--sector-size` | 50 | Sector width, in meters. |
| `--tile-size` | 1024 | Large photos are cut into tiles of this size, so small targets stay visible. |
| `--overlap` | 128 | Tile overlap in pixels, so targets on a tile edge are not lost. |

## How it works

1. Find all photos in the folder and its subfolders.
2. Read the position of the camera from the photo metadata.
3. Cut each photo into overlapping tiles.
4. Run the detector on each tile.
5. Convert tile coordinates to photo coordinates and remove duplicate detections from the overlap areas.
6. Calculate the ground position and sector of each finding.
7. Write the reports.

## Roadmap

- [x] **M0:** package, tests, CI
- [x] **M1:** `scan` command with a zero-shot detector and a CSV report
- [x] **M2:** GPS positions from photo metadata, map sectors, HTML map report
- [ ] **M3:** labeled tent caterpillar dataset and a fine-tuned model
- [ ] **M4:** real-time analysis on the drone or an edge computer
- [ ] **M5:** more pests, and a phone app to count ticks

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md). Adding a new pest is a good first contribution.

## License

[MIT](LICENSE)
