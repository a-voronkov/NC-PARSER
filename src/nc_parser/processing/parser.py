from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import numpy as np
import cv2
from pdfminer.high_level import extract_text as pdf_extract_text
from pytesseract import image_to_string as ocr_image_to_string
from bs4 import BeautifulSoup
import pdfplumber
from pdf2image import convert_from_path
import csv
import subprocess
import zipfile
import re
from charset_normalizer import from_path as detect_encoding_from_path
import ftfy
from pypdf import PdfReader
from nc_parser.core.settings import get_settings
from structlog import get_logger

try:
    from striprtf.striprtf import rtf_to_text  # type: ignore
except Exception:  # pragma: no cover
    rtf_to_text = None  # type: ignore

logger = get_logger(__name__)


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


def _pdf_quick_sanity(path: Path) -> bool:
    """Cheap PDF sanity: open metadata and count pages; ensure EOF marker present.

    Returns True if file looks sane; False to fast-fail.
    """
    try:
        # EOF marker near the end
        with path.open("rb") as f:
            f.seek(max(0, path.stat().st_size - 2048))
            tail = f.read()
            if b"%%EOF" not in tail:
                return False
        # Pages accessible
        reader = PdfReader(str(path))
        if len(reader.pages) < 1:
            return False
        return True
    except Exception:
        return False


def _read_doc_binary_text(path: Path) -> str:
    """Read legacy .doc via antiword; fallback to empty on failure."""
    try:
        res = subprocess.run(
            ["antiword", "-w", "0", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        out = res.stdout.decode("utf-8", errors="ignore")
        return ftfy.fix_text(out).strip()
    except Exception:
        return ""


def _read_rtf_text(path: Path) -> str:
    try:
        if rtf_to_text is None:
            return ""
        raw = path.read_text(encoding="utf-8", errors="ignore")
        txt = rtf_to_text(raw)
        return ftfy.fix_text(txt).strip()
    except Exception:
        return ""


def _read_odt_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            with zf.open("content.xml") as f:
                xml = f.read().decode("utf-8", errors="ignore")
        # Extract visible text; lxml already available
        soup = BeautifulSoup(xml, "lxml")
        txt = soup.get_text("\n")
        return ftfy.fix_text(txt).strip()
    except Exception:
        return ""


def _normalize_output_text(text: str) -> str:
    if not text:
        return ""
    t = ftfy.fix_text(text)
    t = t.replace("\r", "").replace("\xa0", " ")
    # Normalize unicode minus to hyphen
    t = t.replace("−", "-")
    # Collapse excessive spaces but preserve newlines
    t = re.sub(r"[ \t]+", " ", t)
    # Trim trailing spaces on lines
    t = "\n".join(line.rstrip() for line in t.splitlines())
    # Strip UI/noise lines: short, mostly symbols
    def _is_noise(line: str) -> bool:
        if not line:
            return False
        # Remove common bullet-like chars for ratio check
        cleaned = re.sub(r"[A-Za-z0-9]", "", line)
        symbol_ratio = (len(cleaned) / max(1, len(line)))
        if len(line) <= 3 and symbol_ratio > 0.5:
            return True
        # Lines with almost no letters and lots of punctuation/symbols
        letters = len(re.findall(r"[A-Za-zА-Яа-я]", line))
        if letters == 0 and symbol_ratio > 0.6:
            return True
        # UI crumbs like isolated icons repeated
        if re.fullmatch(r"[•·©®™@©\-_=+~^`\|<>\(\)\[\]{}\\]+", line.strip()):
            return True
        return False
    lines = [ln for ln in t.splitlines() if not _is_noise(ln.strip())]
    t = "\n".join(lines)
    return t.strip()


def _extract_html_tables_rows_from_html(raw_html: str) -> list[list[list[str]]]:
    rows_all: list[list[list[str]]] = []
    try:
        soup = BeautifulSoup(raw_html, "lxml")
        for tbl in soup.find_all("table"):
            rows: list[list[str]] = []
            for tr in tbl.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                rows_all.append(rows)
    except Exception:
        pass
    return rows_all


def _extract_docx_tables_rows(path: Path) -> list[list[list[str]]]:
    out: list[list[list[str]]] = []
    try:
        import docx  # type: ignore
        document = docx.Document(str(path))
        for tbl in document.tables:
            rows: list[list[str]] = []
            for row in tbl.rows:
                cells = [ftfy.fix_text(cell.text or "").strip() for cell in row.cells]
                rows.append(cells)
            if rows:
                out.append(rows)
    except Exception:
        pass
    return out


def _extract_odt_tables_rows_from_xml(xml: str) -> list[list[list[str]]]:
    rows_all: list[list[list[str]]] = []
    try:
        soup = BeautifulSoup(xml, "lxml")
        # tags often have names like 'table:table', 'table:table-row', 'table:table-cell'
        for tbl in soup.find_all(lambda tag: isinstance(tag.name, str) and tag.name.endswith("table")):
            rows: list[list[str]] = []
            for tr in tbl.find_all(lambda tag: isinstance(tag.name, str) and tag.name.endswith("table-row")):
                cells = [c.get_text(strip=True) for c in tr.find_all(lambda tag: isinstance(tag.name, str) and tag.name.endswith("table-cell"))]
                if cells:
                    rows.append(cells)
            if rows:
                rows_all.append(rows)
    except Exception:
        pass
    return rows_all


def _extract_delimited_table_rows_from_text(text: str) -> list[list[list[str]]]:
    rows_all: list[list[list[str]]] = []
    try:
        lines = [ln.strip() for ln in text.splitlines()]
        current: list[list[str]] = []
        for ln in lines:
            if (ln.count('|') >= 2) or (ln.count('\t') >= 1):
                parts = [p.strip() for p in re.split(r"\||\t", ln) if p.strip()]
                if len(parts) >= 2:
                    current.append(parts)
                    continue
            if current:
                rows_all.append(current)
                current = []
        if current:
            rows_all.append(current)
    except Exception:
        pass
    return rows_all


def _extract_key_fields_formal_doc(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        def grab(pats: list[str]) -> str:
            for pat in pats:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    return (m.group(1) or '').strip()
            return ''

        fields["work_permit_no"] = grab([r"Work\s*Permit\s*No\.?[:\-]?\s*([A-Za-z0-9\-\/]+)"])
        fields["visa_grant_number"] = grab([r"Visa\s+grant\s+number\s*[:\-]?\s*([A-Za-z0-9]+)"])
        fields["name"] = grab([r"Name\s*[:\-]?\s*([A-Z .'-]+)", r"Name\s+([A-Z .'-]+)"])
        fields["dob"] = grab([r"Date\s*of\s*Birth\s*[:\-]?\s*([0-9]{1,2}\s*[A-Za-z]{3,}\s*[0-9]{2,4}|[0-9]{2}\/[0-9]{2}\/[0-9]{2,4}|[0-9]{1,2}[A-Z]{3}[0-9]{2,4})"])
        fields["nationality"] = grab([r"Nationality\s*[:\-]?\s*([A-Za-z ]+)"])
        fields["passport_no"] = grab([r"Passport(?:\/|\s*or\s*Travel\s*Document)?\s*No\.?[:\-]?\s*([A-Za-z0-9]+)"])
        fields["employer"] = grab([r"Employer\s*[:\-]?\s*([A-Z0-9 ()&.,'-]+)", r"Name of the Employer\s*([A-Z0-9 ()&.,'-]+)"])
        fields["position"] = grab([r"(TECHNICAL\s+SUPERVISOR.*|Supervisor.*|Engineer.*|Manager.*)"])
        fields["date_of_issue"] = grab([r"Date\s*of\s*issue\s*[:\-]?\s*([0-9]{1,2}\s*[A-Za-z]{3,}\s*[0-9]{2,4})"])
        fields["date_of_expiry"] = grab([r"Date\s*of\s*Expiry\s*[:\-]?\s*([0-9]{1,2}\s*[A-Za-z]{3,}\s*[0-9]{2,4})"])
        # Drop empty
        fields = {k: v for k, v in fields.items() if v}
    except Exception:
        fields = {}
    return fields


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
                        # dump into file_id folder
                        try:
                            file_id_part = path.parent.name
                            prefix = f"{file_id_part}/{path.stem}_p{idx}"
                        except Exception:
                            prefix = f"{path.stem}_p{idx}"
                        text = _ocr_from_pil_image(img, dump_prefix=prefix)
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
                        try:
                            file_id_part = path.parent.name
                            prefix = f"{file_id_part}/{path.stem}_img{count}"
                        except Exception:
                            prefix = f"{path.stem}_img{count}"
                        t = _ocr_from_pil_image(im, dump_prefix=prefix)
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


def _cv2_preprocess_for_ocr(pil_img: Image.Image, dump_prefix: str | None = None) -> list[Image.Image]:
    settings = get_settings()
    variants: list[Image.Image] = []
    # Convert PIL -> OpenCV
    img = np.array(pil_img.convert("RGB"))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    # Deskew via moments angle
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    # Try to estimate skew and rotate
    try:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
        angles: list[float] = []
        if lines is not None:
            for line in lines[:200]:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # Consider near-horizontal text lines
                if -45 < angle < 45:
                    angles.append(angle)
        if angles:
            median_angle = float(np.median(angles))
            if abs(median_angle) > 0.5:
                (h, w) = gray.shape[:2]
                M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        pass
    # Thresholds
    th_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    th_mean = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 10)
    th_gauss = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
    # Morphology to connect text
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    morphed = cv2.morphologyEx(th_otsu, cv2.MORPH_OPEN, kernel)
    # Collect variants
    cv_variants = [gray, th_otsu, th_mean, th_gauss, morphed]
    for idx, arr in enumerate(cv_variants):
        try:
            im = Image.fromarray(arr)
            variants.append(im)
            if dump_prefix and (settings.ocr_debug_dump or str(settings.log_level).upper() == "DEBUG"):
                dump_dir = get_settings().data_dir / "artifacts"
                # Save via proper encoding
                out_path = dump_dir / f"{dump_prefix}_cv2_{idx}.png"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out_path), arr)
                try:
                    logger.debug("ocr_dump_saved", path=str(out_path))
                except Exception:
                    pass
        except Exception:
            continue
    return variants


def _save_pil_variant(img: Image.Image, prefix: str, idx: int) -> None:
    try:
        settings = get_settings()
        if not (settings.ocr_debug_dump or str(settings.log_level).upper() == "DEBUG"):
            return
        dump_dir = settings.data_dir / "artifacts"
        dump_dir.mkdir(parents=True, exist_ok=True)
        out_path = dump_dir / f"{prefix}_pil_{idx}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            logger.debug("ocr_dump_try", path=str(out_path))
        except Exception:
            pass
        try:
            img.save(out_path)
            try:
                logger.debug("ocr_dump_saved", path=str(out_path))
            except Exception:
                pass
        except Exception as e:
            try:
                logger.warning("ocr_dump_error", path=str(out_path), error=str(e))
            except Exception:
                pass
    except Exception as e:
        try:
            logger.warning("ocr_dump_error_setup", error=str(e))
        except Exception:
            pass
        return


def _ocr_from_pil_image(pil_img: Image.Image, dump_prefix: str | None = None) -> str:
    settings = get_settings()
    variants: list[Image.Image] = []
    try:
        base = pil_img.convert("RGB")
        # Force dump original
        try:
            if dump_prefix and (settings.ocr_debug_dump or str(settings.log_level).upper() == "DEBUG"):
                dump_dir = settings.data_dir / "artifacts"
                out_path = dump_dir / f"{dump_prefix}_orig.png"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    logger.debug("ocr_dump_try", path=str(out_path))
                except Exception:
                    pass
                try:
                    base.save(out_path)
                    logger.debug("ocr_dump_saved", path=str(out_path))
                except Exception as e:
                    logger.warning("ocr_dump_error", path=str(out_path), error=str(e))
        except Exception as e:
            try:
                logger.warning("ocr_dump_error_setup", error=str(e))
            except Exception:
                pass
        mx = max(base.size)
        if mx < 800:
            base = base.resize((base.width * 3, base.height * 3), Image.LANCZOS)
        elif mx < 1200:
            base = base.resize((base.width * 2, base.height * 2), Image.LANCZOS)
        g = base.convert("L")
        pil_variants = [
            g,
            ImageOps.autocontrast(g),
            ImageEnhance.Contrast(g).enhance(1.8),
            ImageOps.invert(g),
            g.filter(ImageFilter.UnsharpMask(radius=2, percent=150)),
        ]
        for i, v in enumerate(pil_variants):
            variants.append(v)
            if dump_prefix:
                _save_pil_variant(v, dump_prefix, i)
        # OpenCV variants
        variants.extend(_cv2_preprocess_for_ocr(base, dump_prefix=dump_prefix))
    except Exception:
        variants = [pil_img]
    configs = [
        f"--oem 1 --psm {settings.ocr_tesseract_psm}",
        "--oem 3 --psm 6",
        "--oem 3 --psm 4",
        "--oem 3 --psm 7",
        "--oem 1 --psm 11",
        "--oem 1 --psm 12",
        "--oem 1 --psm 13",
        "--oem 1 --psm 6 -c tessedit_char_blacklist=~`^*_{}[]|\\",
        "--oem 1 --psm 6 -c preserve_interword_spaces=1",
    ]
    try:
        logger.info(
            "ocr_attempt_start",
            variants=len(variants),
            dump_enabled=settings.ocr_debug_dump,
            prefix=dump_prefix,
            ocr_langs=settings.ocr_langs,
        )
    except Exception:
        pass
    for im in variants:
        for cfg in configs:
            try:
                text = ocr_image_to_string(im, lang=settings.ocr_langs, config=cfg).strip()
                if text:
                    try:
                        logger.info("ocr_attempt_ok", length=len(text), config=cfg)
                    except Exception:
                        pass
                    return text
            except Exception:
                continue
    try:
        logger.info("ocr_attempt_empty")
    except Exception:
        pass
    return ""


def _read_image_text(path: Path) -> str:
    settings = get_settings()
    with Image.open(path) as img:
        # Put dumps under file_id folder if possible
        try:
            file_id_part = path.parent.name
            dump_prefix = f"{file_id_part}/{path.stem}"
        except Exception:
            dump_prefix = path.stem
        return _ocr_from_pil_image(img, dump_prefix=dump_prefix)


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

    def _detect_type(p: Path) -> str:
        try:
            with p.open("rb") as f:
                head = f.read(4096)
            h = head[:16]
            if head.startswith(b"%PDF"):
                return "pdf"
            if head.startswith(b"\x89PNG\r\n\x1a\n"):
                return "png"
            if head.startswith(b"\xFF\xD8\xFF"):
                return "jpg"
            if head[:2] == b"PK":
                # Could be DOCX/ZIP/ODT; cheap check — rely on suffix next
                return "zip"
            if head[:8] == b"{\\rtf1":
                return "rtf"
            txt_sample = head.decode("utf-8", errors="ignore").lower()
            if "<html" in txt_sample or "<!doctype html" in txt_sample:
                return "html"
            if "," in txt_sample and "\n" in txt_sample:
                return "csv"
            return "txt"
        except Exception:
            return "txt"

    ftype = _detect_type(path)
    try:
        logger.info("detect_file_type", suffix=suffix, ftype=ftype, path=str(path))
    except Exception:
        pass

    if ftype == "txt" or (suffix in {".txt", ""} and ftype is None):
        text = _read_text_file(path)
    elif ftype == "pdf" or suffix == ".pdf":
        if not _pdf_quick_sanity(path):
            return ParsedDocument(full_text="", pages=[])
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
        text = _normalize_output_text(text)
        for p in pages:
            p["text"] = _normalize_output_text(p.get("text", ""))
        return ParsedDocument(full_text=text, pages=pages)
    elif ftype in {"png", "jpg"} or suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        text = _normalize_output_text(_read_image_text(path))
    elif ftype == "docx" or suffix in {".docx"}:
        text = _read_docx_text(path)
        # OCR for embedded images
        image_texts = _extract_docx_images_ocr(path)
        # Extract tables
        docx_tables = _extract_docx_tables_rows(path)
        tables_html = [_render_html_table(rows) for rows in docx_tables]
        tables_plain = [_render_plain_table(rows) for rows in docx_tables]
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
        if tables_plain:
            pages.append({
                "index": len(pages),
                "text": "\n\n".join(tables_plain),
                "elements": [{"type": "table_html", "description": html} for html in tables_html],
            })
            text = (text + "\n\n" + "\n\n".join(tables_plain)).strip()
        text = _normalize_output_text(text)
        for p in pages:
            p["text"] = _normalize_output_text(p.get("text", ""))
        return ParsedDocument(full_text=text, pages=pages if pages else [])
    elif suffix == ".doc":
        text = _normalize_output_text(_read_doc_binary_text(path))
        # Try to extract simple delimited tables from text
        tables_rows = _extract_delimited_table_rows_from_text(text)
        tables_html = [_render_html_table(rows) for rows in tables_rows]
        tables_plain = [_render_plain_table(rows) for rows in tables_rows]
        pages = [{"index": 0, "text": text}]
        if tables_plain:
            pages.append({
                "index": 1,
                "text": "\n\n".join(tables_plain),
                "elements": [{"type": "table_html", "description": html} for html in tables_html],
            })
            text = (text + "\n\n" + "\n\n".join(tables_plain)).strip()
        # Extract known fields
        fields = _extract_key_fields_formal_doc(text)
        if fields:
            pages.append({"index": len(pages), "text": "", "elements": [{"type": "fields", "description": json.dumps(fields, ensure_ascii=False)}]})
        text = _normalize_output_text(text)
        for p in pages:
            p["text"] = _normalize_output_text(p.get("text", ""))
        return ParsedDocument(full_text=text, pages=pages)
    elif ftype == "rtf" or suffix == ".rtf":
        text = _normalize_output_text(_read_rtf_text(path))
        tables_rows = _extract_delimited_table_rows_from_text(text)
        tables_html = [_render_html_table(rows) for rows in tables_rows]
        tables_plain = [_render_plain_table(rows) for rows in tables_rows]
        pages = [{"index": 0, "text": text}]
        if tables_plain:
            pages.append({
                "index": 1,
                "text": "\n\n".join(tables_plain),
                "elements": [{"type": "table_html", "description": html} for html in tables_html],
            })
            text = (text + "\n\n" + "\n\n".join(tables_plain)).strip()
        fields = _extract_key_fields_formal_doc(text)
        if fields:
            pages.append({"index": len(pages), "text": "", "elements": [{"type": "fields", "description": json.dumps(fields, ensure_ascii=False)}]})
        text = _normalize_output_text(text)
        for p in pages:
            p["text"] = _normalize_output_text(p.get("text", ""))
        return ParsedDocument(full_text=text, pages=pages)
    elif suffix == ".odt":
        # Extract text and tables from content.xml
        try:
            with zipfile.ZipFile(str(path), "r") as zf:
                xml = zf.open("content.xml").read().decode("utf-8", errors="ignore")
        except Exception:
            xml = ""
        text = _normalize_output_text(BeautifulSoup(xml, "lxml").get_text("\n") if xml else _read_odt_text(path))
        tables_rows = _extract_odt_tables_rows_from_xml(xml) if xml else []
        tables_html = [_render_html_table(rows) for rows in tables_rows]
        tables_plain = [_render_plain_table(rows) for rows in tables_rows]
        pages = [{"index": 0, "text": text}]
        if tables_plain:
            pages.append({
                "index": 1,
                "text": "\n\n".join(tables_plain),
                "elements": [{"type": "table_html", "description": html} for html in tables_html],
            })
            text = (text + "\n\n" + "\n\n".join(tables_plain)).strip()
        fields = _extract_key_fields_formal_doc(text)
        if fields:
            pages.append({"index": len(pages), "text": "", "elements": [{"type": "fields", "description": json.dumps(fields, ensure_ascii=False)}]})
        text = _normalize_output_text(text)
        for p in pages:
            p["text"] = _normalize_output_text(p.get("text", ""))
        return ParsedDocument(full_text=text, pages=pages)
    elif ftype == "csv" or suffix in {".csv"}:
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
            plain = _normalize_output_text(_render_plain_table(rows))
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
    elif ftype == "html" or suffix in {".html", ".htm"}:
        raw = _read_text_file(path)
        soup = BeautifulSoup(raw, "lxml")
        text = _normalize_output_text(soup.get_text("\n"))
        html_tables_rows = _extract_html_tables_rows_from_html(raw)
        tables_html = [_render_html_table(rows) for rows in html_tables_rows]
        tables_plain = [_render_plain_table(rows) for rows in html_tables_rows]
        pages = [{"index": 0, "text": text}]
        if tables_plain:
            pages.append({
                "index": 1,
                "text": "\n\n".join(tables_plain),
                "elements": [{"type": "table_html", "description": html} for html in tables_html],
            })
            text = (text + "\n\n" + "\n\n".join(tables_plain)).strip()
        return ParsedDocument(full_text=text, pages=pages)
    else:
        text = ""
    text = _normalize_output_text(text)
    pages = [{"index": 0, "text": text}] if text else []
    return ParsedDocument(full_text=text, pages=pages)


