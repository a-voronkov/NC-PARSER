from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass
class Caption:
    text: str
    model: str = "stub"


def caption_image_stub(path: Path) -> Caption:
    with Image.open(path) as img:
        width, height = img.size
        mode = img.mode
    return Caption(text=f"Image {width}x{height}, mode={mode}", model="stub")


