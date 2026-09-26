# TickTerminator

Find pests in drone photos.

Fly a drone over a forest, orchard or nursery. Give the photos to TickTerminator. It tells you which photos show pests, and where in each photo.

The first target is the **eastern tent caterpillar**. Its silk tents are large and easy to see from the air. Ticks are too small for a drone camera, so TickTerminator counts them in close-up photos instead (see [Count ticks](#count-ticks)).

> **Status:** early prototype. The default detector is zero-shot: it finds pests from text descriptions and needs no training data. Results will have errors. Always check a finding before you act on it. For better results, [train a model](#train-a-model) on your own labeled photos.

## Install

Requires Python 3.10 or later.

```bash
git clone https://github.com/jpow18/TickTerminator.git
cd TickTerminator
pip install '.[ml]'
```

The `ml` extra installs PyTorch and Hugging Face Transformers. The first scan downloads the OWLv2 model (about 600 MB).

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
| `.json` | Findings as COCO pre-labels, to correct and use for training. See [Train a model](#train-a-model). |

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
| `--pests` | all drone pests | Comma-separated pest names. See `tickterminator pests`. |
| `--threshold` | 0.2 (OWLv2), 0.5 (trained) | Minimum score, 0 to 1. Increase it to get fewer false detections. |
| `--detector` | `owlv2` | `owlv2` finds pests from text prompts. `trained` uses a model from `tickterminator train`. |
| `--model` | – | Model folder for `--detector trained`. |
| `--output` | `detections.csv`, `report.html` | Report file. Use more than once. |
| `--altitude` | from photo | Flight height above the ground, in meters. |
| `--sector-size` | 50 | Sector width, in meters. |
| `--tile-size` | 1024 | Large photos are cut into tiles of this size, so small targets stay visible. |
| `--overlap` | tile size / 8 | Tile overlap in pixels, so targets on a tile edge are not lost. |

## How it works

1. Find all photos in the folder and its subfolders.
2. Read the position of the camera from the photo metadata.
3. Cut each photo into overlapping tiles.
4. Run the detector on each tile.
5. Convert tile coordinates to photo coordinates and remove duplicate detections from the overlap areas.
6. Calculate the ground position and sector of each finding.
7. Write the reports.

## Train a model

The zero-shot detector is a good start, but a model trained on your own photos is more accurate. The steps:

1. **Make pre-labels.** Scan the photos and write a COCO file:
   ```bash
   tickterminator scan ./flight_photos --pests tent_caterpillar --output prelabels.json
   ```
2. **Correct the labels.** Import the photos and `prelabels.json` into [CVAT](https://www.cvat.ai/) or [Label Studio](https://labelstud.io/) as a COCO dataset. Delete the wrong boxes, add the missing ones, then export as COCO. The category names must stay as the pest names (for example `tent_caterpillar`).
3. **Train.**
   ```bash
   tickterminator train labels.json --images ./flight_photos --output models/tents-v1
   ```
   Training starts from RT-DETR v2 (Apache-2.0 license) and uses the same tiles as the scanner. A GPU makes it much faster. Options: `--epochs` (30), `--batch-size` (4), `--learning-rate` (0.0001), `--base-model`.
4. **Scan with the trained model.**
   ```bash
   tickterminator scan ./new_flight --detector trained --model models/tents-v1
   ```

A few hundred labeled tents is a good start.

## Measure a detector

Keep some labeled photos out of training. Use them to measure how good a detector is:

```bash
tickterminator evaluate test_labels.json --images ./test_photos --detector trained --model models/tents-v1
```

```
40 photos, 112 labels
pest                 threshold labels found correct precision recall    f1 photo f1
tent_caterpillar          0.10    112   160      98      0.61   0.88  0.72     0.93
tent_caterpillar          0.30    112   104      91      0.88   0.81  0.84     0.95
```

- **Precision:** the part of the detections that are correct.
- **Recall:** the part of the labeled pests that the detector found.
- **F1:** one number that combines precision and recall. Higher is better.
- **Photo F1:** the same, but only for the question "does this photo show the pest?".

A detection is correct when it overlaps a label by 50% or more (IoU ≥ 0.5, set with `--iou`). Use the results to select `--threshold` for `scan`, and to compare prompts or models.

## Count ticks

A tick is 1–5 mm, too small for a drone camera. To measure ticks in an area, use a *tick drag*: pull a white cloth (about 1 m²) over the grass for a set distance, then photograph the cloth with a phone. TickTerminator counts the ticks in the photos:

```bash
tickterminator scan ./drag_photos --pests tick --tile-size 512
```

A smaller tile size makes small ticks larger for the detector. Phone photos usually have GPS, but no drone data, so the findings have no map position. The file name and the count for each photo are in the report.

## Scan during the flight

`watch` scans new photos as they arrive in a folder, and prints each finding immediately:

```bash
tickterminator watch ./incoming --output live.html --stop-after-idle 300
```

```
./incoming/DJI_0042.JPG: 1 findings
FOUND tent_caterpillar (0.71) at 45.500032, -73.250042
```

Point it at the folder where photos arrive: an SD card, a folder that syncs from the drone app, or a folder on a small computer on the drone that saves camera frames. It reads a photo only when the file is completely written. It updates the reports after each photo with findings, and again when it stops. Stop it with Ctrl+C, or use `--stop-after-idle SECONDS`, for example when the drone lands.

Sector labels can change during a flight, because the flight area grows. Use the final report for sectors.

**Hardware.** The same code runs on a laptop at the field or on an edge computer with a GPU, such as an NVIDIA Jetson. OWLv2 is slow without a GPU. A trained RT-DETR model is much faster. Speed on each device is not measured yet.

## Roadmap

- [x] **M0:** package, tests, CI
- [x] **M1:** `scan` command with a zero-shot detector and a CSV report
- [x] **M2:** GPS positions from photo metadata, map sectors, HTML map report
- [x] **M3:** pre-labels, training command and trained detector
- [ ] **M3b:** a public labeled tent caterpillar dataset and a published model
- [x] **M4:** `watch` command for real-time scans
- [ ] **M4b:** speed tests on edge hardware, and ONNX export for faster models
- [x] **M5:** more pests (bagworm), and tick counts from close-up photos
- [ ] **M6:** phone app for tick counts in the field

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md). Adding a new pest is a good first contribution.

## License

[MIT](LICENSE)
