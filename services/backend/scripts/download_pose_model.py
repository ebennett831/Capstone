"""Explicitly download and verify the official Pose Landmarker Lite model."""

import argparse
from collections.abc import Sequence
import hashlib
import os
from pathlib import Path
import sys
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from backend.vision import POSE_MODEL_FILENAME, POSE_MODEL_VARIANT


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
MODEL_SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
DEFAULT_MODEL_PATH = Path(__file__).parents[1] / "models" / POSE_MODEL_FILENAME


def download_model(destination: Path, *, force: bool = False) -> Path:
    """Download the pinned model and publish it only after checksum validation."""
    destination = destination.expanduser().resolve()
    if destination.exists() and not force:
        if _sha256(destination) == MODEL_SHA256:
            print(f"Verified existing {POSE_MODEL_VARIANT} model: {destination}")
            return destination
        raise OSError(
            f"Existing model has an unexpected checksum: {destination}. "
            "Use --force to replace it."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(
        f".{destination.name}.{uuid4().hex}.download"
    )
    try:
        with urlopen(MODEL_URL, timeout=60) as response, temporary_path.open(
            "wb"
        ) as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)

        actual_sha256 = _sha256(temporary_path)
        if actual_sha256 != MODEL_SHA256:
            raise OSError(
                "Downloaded model checksum did not match the pinned official asset: "
                f"expected {MODEL_SHA256}, got {actual_sha256}"
            )
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(f"Downloaded {POSE_MODEL_VARIANT} model to: {destination}")
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=f"Download the official {POSE_MODEL_VARIANT} model."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Model output path (default: {DEFAULT_MODEL_PATH}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing model file after downloading and verifying it.",
    )
    args = parser.parse_args(argv)

    try:
        download_model(args.output, force=args.force)
    except (OSError, URLError) as error:
        print(f"Model download failed: {error}", file=sys.stderr)
        return 1
    return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
