"""End-to-end training with a tiny random model. Needs the `ml` extra."""

import csv
import json

import pytest
from PIL import Image, ImageDraw

pytest.importorskip("torch")
pytest.importorskip("torchvision")
transformers = pytest.importorskip("transformers")

from tickterminator import cli  # noqa: E402


@pytest.fixture
def tiny_base_model(tmp_path):
    backbone = transformers.RTDetrResNetConfig(
        embedding_size=16,
        hidden_sizes=[16, 32, 64, 128],
        depths=[1, 1, 1, 1],
        out_features=["stage2", "stage3", "stage4"],
    )
    config = transformers.RTDetrV2Config(
        backbone_config=backbone,
        encoder_hidden_dim=32,
        encoder_in_channels=[32, 64, 128],
        d_model=32,
        decoder_in_channels=[32, 32, 32],
        encoder_ffn_dim=64,
        decoder_ffn_dim=64,
        encoder_layers=1,
        decoder_layers=2,
        encoder_attention_heads=2,
        decoder_attention_heads=2,
        num_queries=10,
        num_denoising=4,
    )
    folder = tmp_path / "base"
    transformers.RTDetrV2ForObjectDetection(config).save_pretrained(folder)
    transformers.RTDetrImageProcessor(size={"height": 64, "width": 64}).save_pretrained(folder)
    return folder


@pytest.fixture
def labeled_photos(tmp_path):
    folder = tmp_path / "photos"
    folder.mkdir()
    images, annotations = [], []
    for image_id in (1, 2):
        image = Image.new("RGB", (128, 128), "green")
        ImageDraw.Draw(image).ellipse((20, 20, 50, 50), fill="white")
        image.save(folder / f"{image_id}.jpg")
        images.append({"id": image_id, "file_name": f"{image_id}.jpg", "width": 128, "height": 128})
        annotations.append(
            {"id": image_id, "image_id": image_id, "category_id": 7, "bbox": [20, 20, 30, 30]}
        )
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "images": images,
                "annotations": annotations,
                "categories": [{"id": 7, "name": "tent_caterpillar"}],
            }
        )
    )
    return labels, folder


def test_train_then_scan_with_trained_model(tiny_base_model, labeled_photos, tmp_path):
    labels, photos = labeled_photos
    model = tmp_path / "model"

    cli.main(
        ["train", str(labels), "--images", str(photos), "--output", str(model),
         "--base-model", str(tiny_base_model), "--epochs", "1", "--batch-size", "2",
         "--tile-size", "64", "--overlap", "0"]
    )  # fmt: skip

    assert json.loads((model / "config.json").read_text())["id2label"] == {"0": "tent_caterpillar"}

    report = tmp_path / "report.csv"
    cli.main(
        ["scan", str(photos), "--detector", "trained", "--model", str(model),
         "--threshold", "0", "--tile-size", "64", "--output", str(report)]
    )  # fmt: skip

    with report.open() as file:
        rows = list(csv.DictReader(file))
    assert rows
    assert {row["pest"] for row in rows} == {"tent_caterpillar"}


def test_training_can_continue_from_an_epoch_checkpoint(tiny_base_model, labeled_photos, tmp_path):
    labels, photos = labeled_photos
    common = ["--images", str(photos), "--batch-size", "2", "--tile-size", "64", "--overlap", "0"]
    first = tmp_path / "first"
    cli.main(
        ["train", str(labels), "--output", str(first), "--base-model", str(tiny_base_model),
         "--epochs", "2", *common]
    )  # fmt: skip
    checkpoints = sorted(path.name for path in (first / "checkpoints").iterdir())
    assert checkpoints == ["epoch-1", "epoch-2"]

    second = tmp_path / "second"
    cli.main(
        ["train", str(labels), "--output", str(second),
         "--base-model", str(first / "checkpoints" / "epoch-2"), "--epochs", "1", *common]
    )  # fmt: skip
    assert (second / "model.safetensors").exists()
