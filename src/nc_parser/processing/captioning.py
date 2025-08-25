from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import json
import hashlib
from io import BytesIO

from PIL import Image
from nc_parser.core.settings import get_settings


@dataclass
class Caption:
    text: str
    model: str = "stub"


class Captioner:
    """Abstract captioner interface for batching PIL images.

    Implementations should be pure and side-effect free, returning one Caption per input image.
    """

    model_name: str = "unknown"

    def caption_pil_batch(self, images: list[Image.Image]) -> list[Caption]:  # pragma: no cover - interface
        raise NotImplementedError


class StubCaptioner(Captioner):
    """Trivial captioner that describes size and mode."""

    model_name = "stub"

    def caption_pil_batch(self, images: list[Image.Image]) -> list[Caption]:
        out: list[Caption] = []
        for img in images:
            width, height = img.size
            mode = img.mode
            out.append(Caption(text=f"Image {width}x{height}, mode={mode}", model=self.model_name))
        return out


class Blip2Captioner(Captioner):  # lightweight placeholder
    """Placeholder for BLIP-2 backend.

    Real implementation should load the model on the configured device and batch infer.
    For now, we return a stub text but mark the model as blip2-stub.
    """

    model_name = "blip2-stub"

    def caption_pil_batch(self, images: list[Image.Image]) -> list[Caption]:
        out: list[Caption] = []
        for img in images:
            width, height = img.size
            out.append(Caption(text=f"Visual description (stub) for {width}x{height}", model=self.model_name))
        return out


class QwenVLCaptioner(Captioner):  # lightweight placeholder
    """Placeholder for Qwen-VL backend.

    Real implementation should load the model on the configured device and batch infer.
    For now, we return a stub text but mark the model as qwen-vl-stub.
    """

    model_name = "qwen-vl-stub"

    def caption_pil_batch(self, images: list[Image.Image]) -> list[Caption]:
        out: list[Caption] = []
        for img in images:
            width, height = img.size
            out.append(Caption(text=f"Visual description (stub) for {width}x{height}", model=self.model_name))
        return out


def build_captioner() -> Captioner:
    """Factory for captioner backend based on settings."""
    s = get_settings()
    backend = (s.caption_backend or "stub").lower()
    if backend == "blip2":
        return Blip2Captioner()
    if backend in {"qwen_vl", "qwen", "qwen-vl"}:
        return QwenVLCaptioner()
    return StubCaptioner()


def _get_cache_dir() -> Path:
    s = get_settings()
    if s.caption_cache_dir is not None:
        return Path(s.caption_cache_dir)
    return s.data_dir / "artifacts" / "caption_cache"


def _image_hash(img: Image.Image) -> str:
    """Compute stable hash for an image content.

    We resize to a bounded max dimension to limit hash cost, and hash PNG bytes.
    """
    max_dim = 512
    im = img
    mx = max(im.size)
    if mx > max_dim:
        ratio = max_dim / float(mx)
        im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    # Use RGB to be stable across modes
    im.convert("RGB").save(buf, format="PNG", optimize=False)
    data = buf.getvalue()
    return hashlib.sha256(data).hexdigest()


def _cache_read(key: str) -> Caption | None:
    try:
        path = _get_cache_dir() / f"{key}.json"
        if not path.exists():
            return None
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return None
        text = obj.get("text") or ""
        model = obj.get("model") or "stub"
        return Caption(text=text, model=model)
    except Exception:
        return None


def _cache_write(key: str, cap: Caption) -> None:
    try:
        d = _get_cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{key}.json"
        obj = {"text": cap.text, "model": cap.model}
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    except Exception:
        return


def caption_images_with_cache(images: list[Image.Image]) -> tuple[list[Caption], dict[str, Any]]:
    """Caption images with caching according to settings.

    Returns (captions, metrics).
    metrics keys: cache_hits, processed
    """
    s = get_settings()
    captioner = build_captioner()
    keys: list[str] = []
    hits: list[Caption | None] = []
    cache_hits = 0
    need_proc_imgs: list[Image.Image] = []
    need_proc_idx: list[int] = []
    if not images:
        return [], {"cache_hits": 0, "processed": 0, "model": captioner.model_name}
    for idx, img in enumerate(images):
        k = _image_hash(img)
        keys.append(k)
        cap: Caption | None = None
        if s.caption_cache_enabled:
            cap = _cache_read(k)
        if cap is not None:
            hits.append(cap)
            cache_hits += 1
        else:
            hits.append(None)
            need_proc_idx.append(idx)
            need_proc_imgs.append(img)
    # Batch according to batch size
    produced: list[Caption] = []
    if need_proc_imgs:
        bs = max(1, int(s.caption_batch_size or 8))
        for i in range(0, len(need_proc_imgs), bs):
            batch = need_proc_imgs[i:i+bs]
            produced.extend(captioner.caption_pil_batch(batch))
    # Merge results in original order
    out: list[Caption] = []
    produced_iter = iter(produced)
    for idx, prev in enumerate(hits):
        if prev is not None:
            out.append(prev)
        else:
            cap = next(produced_iter)
            out.append(cap)
            if s.caption_cache_enabled:
                _cache_write(keys[idx], cap)
    return out, {"cache_hits": cache_hits, "processed": len(need_proc_imgs), "model": captioner.model_name}


def caption_image_pil(img: Image.Image) -> Caption:
    """Stub captioner for a PIL image.

    Returns a trivial description with size and mode; replace with real backend later.
    """
    width, height = img.size
    mode = img.mode
    return Caption(text=f"Image {width}x{height}, mode={mode}", model="stub")


def caption_image_stub(path: Path) -> Caption:
    """Compatibility wrapper for old code paths that pass a Path.

    Uses caching and current backend to produce a single caption.
    """
    with Image.open(path) as img:
        caps, _ = caption_images_with_cache([img])
        return caps[0] if caps else Caption(text="", model="stub")

