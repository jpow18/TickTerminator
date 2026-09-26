import random
from collections.abc import Callable, Iterator, Sequence
from dataclasses import astuple, dataclass
from pathlib import Path
from statistics import mean

from tickterminator import coco
from tickterminator.labels import LabeledPhoto, pests_in
from tickterminator.ml import default_device, torch, transformers
from tickterminator.pests import Pest
from tickterminator.photos import load_image
from tickterminator.tiling import TilingConfig
from tickterminator.training.dataset import TrainingTile, training_tiles

DEFAULT_BASE_MODEL = "PekingU/rtdetr_v2_r18vd"


@dataclass(frozen=True)
class TrainingConfig:
    base_model: str = DEFAULT_BASE_MODEL
    """Hugging Face model name or folder. RT-DETR v2 is fast and has an Apache-2.0 license."""
    epochs: int = 30
    batch_size: int = 4
    learning_rate: float = 1e-4
    tiling: TilingConfig = TilingConfig()
    seed: int = 0


EpochCallback = Callable[[int, float], None]


def train(
    photos: list[LabeledPhoto],
    output_dir: Path,
    config: TrainingConfig,
    on_epoch: EpochCallback = lambda epoch, loss: None,
    device: str | None = None,
) -> None:
    """Fine-tune `config.base_model` and save the model to `output_dir`."""
    pests = pests_in(photos)
    if not pests:
        raise ValueError("The labels contain no boxes.")
    label_ids = {pest: index for index, pest in enumerate(pests)}
    device = device or default_device()
    rng = random.Random(config.seed)
    torch.manual_seed(config.seed)

    processor = transformers.AutoImageProcessor.from_pretrained(config.base_model)
    model = transformers.AutoModelForObjectDetection.from_pretrained(
        config.base_model,
        id2label={index: pest.name.lower() for pest, index in label_ids.items()},
        label2id={pest.name.lower(): index for pest, index in label_ids.items()},
        ignore_mismatched_sizes=True,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)
    tiles = training_tiles(photos, config.tiling, rng)

    model.train()
    for epoch in range(1, config.epochs + 1):
        rng.shuffle(tiles)
        losses = [
            train_step(model, processor, optimizer, batch, label_ids, device)
            for batch in batches(tiles, config.batch_size)
        ]
        save_model(model, processor, checkpoint_dir(output_dir, epoch))
        on_epoch(epoch, mean(losses))

    save_model(model, processor, output_dir)


def checkpoint_dir(output_dir: Path, epoch: int) -> Path:
    """A model folder for each epoch. To continue a stopped training, use it as the base model."""
    return output_dir / "checkpoints" / f"epoch-{epoch}"


def save_model(model, processor, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(folder)
    processor.save_pretrained(folder)


def train_step(
    model,
    processor,
    optimizer,
    batch: Sequence[TrainingTile],
    label_ids: dict[Pest, int],
    device: str,
) -> float:
    images = [load_image(tile.photo_path).crop(astuple(tile.region)) for tile in batch]
    annotations = [coco_target(index, tile, label_ids) for index, tile in enumerate(batch)]
    inputs = processor(images=images, annotations=annotations, return_tensors="pt")
    labels = [
        {key: value.to(device) for key, value in target.items()} for target in inputs["labels"]
    ]

    loss = model(pixel_values=inputs["pixel_values"].to(device), labels=labels).loss
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    return loss.item()


def coco_target(image_id: int, tile: TrainingTile, label_ids: dict[Pest, int]) -> dict:
    return {
        "image_id": image_id,
        "annotations": [
            {
                "bbox": coco.coco_bbox(label.box),
                "category_id": label_ids[label.pest],
                "area": label.box.area,
                "iscrowd": 0,
            }
            for label in tile.labels
        ],
    }


def batches(items: Sequence, size: int) -> Iterator[Sequence]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
