"""Optional machine-learning packages. Import them from here to get a clear error when missing."""

try:
    import scipy  # noqa: F401  (transformers needs it for OWLv2)
    import torch
    import torchvision  # noqa: F401  (transformers needs it for image processors)
    import transformers
except ImportError as error:
    raise ImportError(
        "This needs extra packages. Install them with: pip install 'tickterminator[ml]'"
    ) from error

__all__ = ["default_device", "torch", "transformers"]


def default_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
