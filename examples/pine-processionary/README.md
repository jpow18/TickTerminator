# Pine processionary moth nests

Five small photos of pine processionary moth nests (*Thaumetopoea pityocampa*) with 7 labeled nests. Use them to test prompts and settings quickly:

```bash
tickterminator evaluate examples/pine-processionary/labels.json --images examples/pine-processionary/images
```

These are **not drone photos**: they were taken from the ground. The set is too small to measure a detector reliably. It only shows if a change makes the results better or worse.

## Source and license

The photos are Figure S1 of the supplementary material of Garcia A, Samalens J-C, Grillet A, Soares P, Branco M, van Halder I, Jactel H, Battisti A (2023), *Testing early detection of pine processionary moth Thaumetopoea pityocampa nests using UAV-based methods*, NeoBiota 84: 267–279, <https://doi.org/10.3897/neobiota.84.95692>. The supplementary material is published under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) at <https://zenodo.org/records/7952440>.

The labels in `labels.json` (COCO format) were made for TickTerminator. One photo of the figure (a view over a whole stand) is not included, because its nests are too small to label.

## Results with the zero-shot detector (OWLv2)

| Prompts | Threshold | Correct nests | Precision | Recall | F1 |
|---|---|---|---|---|---|
| "white silk nest at the tip of a pine branch", "silk caterpillar nest in a pine tree" | best (0.08) | 2 of 7 | 0.14 | 0.29 | 0.19 |
| "white cocoon", "white fluffy ball" (current) | 0.04 | 5 of 7 | 1.00 | 0.71 | 0.83 |

Short, concrete phrases worked better than long descriptions. The prompts and the threshold were selected on these same photos, so expect lower results on new photos.
