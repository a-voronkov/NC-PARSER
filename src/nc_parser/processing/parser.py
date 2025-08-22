from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageEnhance
from pdfminer.high_level import extract_text as pdf_extract_text
from pytesseract import image_to_string as ocr_image_to_string
from bs4 import BeautifulSoup
import pdfplumber
from pdf2image import convert_from_path
import csv
from charset_normalizer import from_path as detect_encoding_from_path
import ftfy
from pypdf import PdfReader
from nc_parser.core.settings import get_settings


@dataclass
class ParsedDocument:
    full_text: str
    pages: list[dict[str, Any]]


def _read_text_file(path: Path) -> str:
    try:
        # Try UTF-8 first
        return path.read_text(encoding="utf-8", errors="strict")
    except Exception:
        try:
            best = detect_encoding_from_path(str(path)).best()
            if best is not None:
                return best.output_text(stripped=True)
        except Exception:
            pass
        # Fallback with ignore to always return something
        txt = path.read_text(encoding="utf-8", errors="ignore")
        return ftfy.fix_text(txt)


def _read_pdf_text(path: Path) -> str:
    return pdf_extract_text(str(path)) or ""


def _extract_pdf_tables_html(path: Path) -> list[str]:
    html_tables: list[str] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for tbl in tables or []:
                    # Render minimal HTML table
                    rows = [
                        "<tr>" + "".join(f"<td>{(cell or '').strip()}</td>" for cell in row) + "</tr>"
                        for row in tbl
                    ]
                    html = "<table>" + "".join(rows) + "</table>"
                    html_tables.append(html)
    except Exception:
        pass
    return html_tables


def _read_pdf_text_plumber(path: Path) -> str:
    try:
        texts: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                texts.append(t)
        return "\n".join(texts).strip()
    except Exception:
        return ""


def _read_pdf_text_hybrid(path: Path) -> str:
    """Extract text per-page; if a page has no text, OCR just that page.

    Respects NC_OCR_PDF_PAGE_LIMIT for OCR part.
    """
    settings = get_settings()
    ocr_limit = max(0, settings.ocr_pdf_page_limit or 0)
    texts: list[str] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            total_pages = len(pdf.pages)
            for idx, page in enumerate(pdf.pages, start=1):
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                if t.strip():
                    texts.append(t.strip())
                    continue
                # OCR this page if within limit
                if ocr_limit and idx > ocr_limit:
                    texts.append("")
                    continue
                try:
                    images = convert_from_path(
                        str(path), dpi=300, first_page=idx, last_page=idx
                    )
                    if images:
                        img = images[0]
                        # Reuse image OCR pipeline by passing through PIL path is not needed
                        # Apply same preprocessing and configs
                        g = img.convert("L")
                        # quick autocontrast to help
                        try:
                            g = ImageOps.autocontrast(g)
                        except Exception:
                            pass
                        text = ocr_image_to_string(
                            g, lang=settings.ocr_langs, config=f"--oem 1 --psm 6"
                        ).strip()
                        texts.append(text)
                    else:
                        texts.append("")
                except Exception:
                    texts.append("")
    except Exception:
        return ""
    return "\n".join(texts).strip()


def _extract_pdf_images_ocr(path: Path, max_images: int = 10) -> list[str]:
    texts: list[str] = []
    try:
        reader = PdfReader(str(path))
        count = 0
        for page in reader.pages:
            try:
                xobjs = page.images  # type: ignore[attr-defined]
            except Exception:
                xobjs = []
            for img in xobjs:
                if count >= max_images:
                    break
                try:
                    from io import BytesIO

                    with Image.open(BytesIO(img.data)) as im:  # type: ignore[attr-defined]
                        # preprocess similar to image pipeline
                        base = im.convert("RGB")
                        if max(base.size) < 1200:
                            base = base.resize((base.width * 2, base.height * 2), Image.LANCZOS)
                        g = base.convert("L")
                        try:
                            g = ImageOps.autocontrast(g)
                        except Exception:
                            pass
                        t = ocr_image_to_string(g, lang=get_settings().ocr_langs, config="--oem 1 --psm 6").strip()
                        if t:
                            texts.append(t)
                            count += 1
                except Exception:
                    continue
            if count >= max_images:
                break
    except Exception:
        return []
    return texts


def _read_image_text(path: Path) -> str:
    settings = get_settings()
    with Image.open(path) as img:
        variants: list[Image.Image] = []
        try:
            base = img.convert("RGB")
            # Upscale small images to help Tesseract
            max_dim = max(base.size)
            if max_dim < 1200:
                scale = 2
                base = base.resize((base.width * scale, base.height * scale), Image.LANCZOS)
            g = base.convert("L")
            variants.append(g)
            # Autocontrast
            variants.append(ImageOps.autocontrast(g))
            # Increase contrast
            variants.append(ImageEnhance.Contrast(g).enhance(1.8))
            # Binary thresholds
            for th in (120, 140, 160, 180):
                try:
                    variants.append(g.point(lambda x, t=th: 0 if x < t else 255, "1"))
                except Exception:
                    continue
        except Exception:
            variants.append(img)
        # Try a set of configs across variants
        configs = [
            f"--oem 1 --psm {settings.ocr_tesseract_psm}",
            "--oem 3 --psm 6",
            "--oem 3 --psm 4",
            "--oem 3 --psm 7",
            "--oem 1 --psm 11",
            "--oem 1 --psm 12",
            "--oem 1 --psm 13",
        ]
        for im in variants:
            for cfg in configs:
                try:
                    text = ocr_image_to_string(im, lang=settings.ocr_langs, config=cfg).strip()
                    if text:
                        return text
                except Exception:
                    continue
        return ""


def _pdf_has_text_layer(path: Path) -> bool:
    try:
        txt = pdf_extract_text(str(path))
        return bool(txt and txt.strip())
    except Exception:
        return False


def _ocr_pdf_pages_to_text(path: Path, dpi: int = 300) -> str:
    settings = get_settings()
    limit = settings.ocr_pdf_page_limit
    # Use first_page/last_page to avoid rendering all pages
    images = convert_from_path(str(path), dpi=dpi, first_page=1, last_page=limit if limit else None)
    texts: list[str] = []
    for img in images:
        texts.append(ocr_image_to_string(img, lang=settings.ocr_langs, config=f"--psm {settings.ocr_tesseract_psm}"))
    return "\n".join(texts)


def _extract_pdf_tables_rows(path: Path) -> list[list[list[str]]]:
    tables_rows: list[list[list[str]]] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for tbl in tables or []:
                    rows: list[list[str]] = []
                    for row in tbl:
                        cells = [(cell or "").strip() for cell in row]
                        rows.append(cells)
                    if rows:
                        tables_rows.append(rows)
    except Exception:
        pass
    return tables_rows


def _render_html_table(rows: list[list[str]]) -> str:
    tr_list = [
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    ]
    return "<table>" + "".join(tr_list) + "</table>"


def _render_plain_table(rows: list[list[str]]) -> str:
    return "\n".join(" | ".join(row) for row in rows)


def _read_docx_text(path: Path) -> str:
    try:
        import docx  # type: ignore
    except Exception:
        return ""
    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_docx_images_ocr(path: Path) -> list[str]:
    try:
        import docx  # type: ignore
    except Exception:
        return []
    texts: list[str] = []
    document = docx.Document(str(path))
    # Iterate related parts to find images
    try:
        rel_parts = document.part.related_parts
        for rel_id, part in rel_parts.items():  # type: ignore[assignment]
            try:
                if getattr(part, "content_type", "").startswith("image/"):
                    from io import BytesIO

                    with Image.open(BytesIO(part.blob)) as img:  # type: ignore[attr-defined]
                        # Reuse image OCR pipeline
                        tmp_path = path  # not used; call OCR directly on PIL image
                        # Preprocess similar to _read_image_text
                        im = img
                        try:
                            if max(im.size) < 1200:
                                im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
                            im = im.convert("L")
                            im = im.point(lambda x: 0 if x < 140 else 255, "1")
                        except Exception:
                            pass
                        configs = ["--oem 1 --psm 6", "--oem 1 --psm 3", "--oem 1 --psm 11"]
                        for cfg in configs:
                            t = ocr_image_to_string(im, lang=get_settings().ocr_langs, config=cfg).strip()
                            if t:
                                texts.append(t)
                                break
            except Exception:
                continue
    except Exception:
        pass
    return texts


def parse_document_to_text(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix in {".txt", ""}:
        text = _read_text_file(path)
    elif suffix == ".pdf":
        if _pdf_has_text_layer(path):
            # Hybrid: try per-page; OCR only empty pages
            text = _read_pdf_text_hybrid(path) or _read_pdf_text_plumber(path) or _read_pdf_text(path)
            if not text:
                # Fallback to OCR for tricky text-layer PDFs
                text = _ocr_pdf_pages_to_text(path)
        else:
            # Guard rails for OCR on big docs
            settings = get_settings()
            size_mb = path.stat().st_size / (1024 * 1024)
            try:
                with pdfplumber.open(str(path)) as pdf:
                    num_pages = len(pdf.pages)
            except Exception:
                num_pages = 0
            if size_mb > settings.ocr_pdf_max_mb or (settings.ocr_pdf_max_pages and num_pages > settings.ocr_pdf_max_pages):
                text = ""  # skip OCR
            else:
                text = _ocr_pdf_pages_to_text(path)
        tables = _extract_pdf_tables_rows(path)
        pages: list[dict[str, Any]] = [{"index": 0, "text": text}]
        # OCR embedded images if text is still weak
        image_texts = _extract_pdf_images_ocr(path)
        if image_texts:
            pages.append({
                "index": len(pages),
                "text": "\n\n".join(image_texts),
                "elements": [{"type": "image_ocr", "description": t} for t in image_texts],
            })
            text = (text + "\n\n" + "\n\n".join(image_texts)).strip()
        if tables:
            tables_html = [_render_html_table(rows) for rows in tables]
            tables_plain = [_render_plain_table(rows) for rows in tables]
            # Add tables page with HTML elements and plain text content
            elements = [{"type": "table_html", "description": html} for html in tables_html]
            pages.append({"index": 1, "text": "\n\n".join(tables_plain), "elements": elements})
            # Concatenate plain tables to full text for searchability
            text = (text + "\n\n" + "\n\n".join(tables_plain)).strip()
        return ParsedDocument(full_text=text, pages=pages)
    elif suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        text = _read_image_text(path)
    elif suffix in {".docx"}:
        text = _read_docx_text(path)
        # OCR for embedded images
        image_texts = _extract_docx_images_ocr(path)
        pages: list[dict[str, Any]] = []
        if text:
            pages.append({"index": 0, "text": text})
        if image_texts:
            pages.append({
                "index": len(pages),
                "text": "\n\n".join(image_texts),
                "elements": [{"type": "image_ocr", "description": t} for t in image_texts],
            })
            text = (text + "\n\n" + "\n\n".join(image_texts)).strip()
        return ParsedDocument(full_text=text, pages=pages if pages else [])
    elif suffix in {".csv"}:
        # Parse CSV to HTML table and plain text
        try:
            # Detect encoding
            enc_text = None
            try:
                best = detect_encoding_from_path(str(path)).best()
                if best is not None:
                    enc_text = best.output_text(stripped=False)
            except Exception:
                enc_text = None
            rows: list[list[str]] = []
            if enc_text is not None:
                # Read from normalized text
                for line in ftfy.fix_text(enc_text).splitlines():
                    # Use csv reader on a list with single line to preserve parsing rules
                    for row in csv.reader([line]):
                        rows.append([col.strip(" \t\ufeff") for col in row])
            else:
                with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        rows.append([ftfy.fix_text(col).strip(" \t\ufeff") for col in row])
            html = _render_html_table(rows)
            plain = ftfy.fix_text(_render_plain_table(rows))
            pages = [
                {"index": 0, "text": plain, "elements": [{"type": "table_html", "description": html}]}
            ]
            return ParsedDocument(full_text=plain, pages=pages)
        except Exception:
            text = ""
    elif suffix in {".md", ".markdown"}:
        # Simple markdown strip: remove fenced code markers and headers
        raw = _read_text_file(path)
        text = raw.replace("```", "\n").replace("#", "").strip()
    elif suffix in {".html", ".htm"}:
        raw = _read_text_file(path)
        soup = BeautifulSoup(raw, "lxml")
        text = soup.get_text("\n")
    else:
        text = ""
    pages = [{"index": 0, "text": text}] if text else []
    return ParsedDocument(full_text=text, pages=pages)


