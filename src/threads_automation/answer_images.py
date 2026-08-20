from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from .paths import ANSWER_IMAGE_DIR, INSTAGRAM_IMAGE_DIR

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def validate_answer_image(content_id: str, threads_path: Path | None = None,
                          instagram_path: Path | None = None) -> dict:
    threads_path = threads_path or (ANSWER_IMAGE_DIR / f"{content_id}-answer.png")
    instagram_path = instagram_path or (INSTAGRAM_IMAGE_DIR / f"{content_id}-answer.png")
    expected_name = f"{content_id}-answer.png"
    if threads_path.name != expected_name or instagram_path.name != expected_name:
        raise ValueError("Answer image filename must match content_id")
    if not threads_path.is_file() or not instagram_path.is_file():
        raise FileNotFoundError(f"Answer image missing for {content_id}")
    data = threads_path.read_bytes()
    if len(data) < 26 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ValueError(f"Answer image must be PNG: {content_id}")
    width, height = struct.unpack(">II", data[16:24])
    bit_depth, color_type = data[24], data[25]
    if (width, height) != (1080, 1350):
        raise ValueError(f"Answer image must be 1080x1350: {content_id}")
    if (bit_depth, color_type) != (8, 2):
        raise ValueError(f"Answer image must be 8-bit RGB: {content_id}")
    if data != instagram_path.read_bytes():
        raise ValueError(f"Instagram/Threads answer image mismatch: {content_id}")
    return {"content_id": content_id, "format": "PNG", "mode": "RGB",
            "size": [width, height], "sha256": hashlib.sha256(data).hexdigest()}
