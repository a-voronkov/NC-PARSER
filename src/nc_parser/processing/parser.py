from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image
from pdfminer.high_level import extract_text as pdf_extract_text
from pytesseract import image_to_string as ocr_image_to_string
from bs4 import BeautifulSoup


@dataclass
class ParsedDocument:
    full_text: str
    pages: list[dict[str, Any]]


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf_text(path: Path) -> str:
    return pdf_extract_text(str(path)) or ""


def _read_image_text(path: Path) -> str:
    with Image.open(path) as img:
        return ocr_image_to_string(img)


def _read_docx_text(path: Path) -> str:
    try:
        import docx  # type: ignore
    except Exception:
        return ""
    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def parse_document_to_text(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix in {".txt", ""}:
        text = _read_text_file(path)
    elif suffix == ".pdf":
        text = _read_pdf_text(path)
    elif suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        text = _read_image_text(path)
    elif suffix in {".docx"}:
        text = _read_docx_text(path)
    elif suffix in {".md", ".markdown"}:
        # Simple markdown strip: remove fenced code markers and headers
        raw = _read_text_file(path)
        text = raw.replace("```", "\n").replace("#", "").strip()
    elif suffix in {".html", ".htm"}:
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
        text = soup.get_text("\n")
    else:
        text = ""
    pages = [{"index": 0, "text": text}] if text else []
    return ParsedDocument(full_text=text, pages=pages)


