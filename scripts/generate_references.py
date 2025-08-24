import sys
import json
import re
from datetime import datetime
from pathlib import Path

# Local package path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nc_parser.processing.parser import (  # noqa: E402
    parse_document_to_text,
)

# Best-effort imports of internals for multi-pass PDF handling
try:  # noqa: SIM105
    from nc_parser.processing.parser import (  # type: ignore # noqa: E402
        _read_pdf_text as pdf_text_simple,
        _read_pdf_text_plumber as pdf_text_plumber,
        _ocr_pdf_pages_to_text as pdf_text_ocr_pages,
        _extract_pdf_tables_rows as pdf_tables_rows,
        _render_html_table as render_html_table,
    )
except Exception:  # pragma: no cover
    pdf_text_simple = None  # type: ignore
    pdf_text_plumber = None  # type: ignore
    pdf_text_ocr_pages = None  # type: ignore
    pdf_tables_rows = None  # type: ignore
    render_html_table = None  # type: ignore


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s2 = s.replace("\ufeff", "").replace("\r", "").replace("\xa0", " ")
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def choose_best_text(candidates: list[str]) -> str:
    # Prefer the longest non-empty normalized candidate
    best = ""
    for c in candidates:
        c2 = normalize_text(c or "")
        if len(c2) > len(best):
            best = c2
    return best


def build_reference_for_file(path: Path) -> dict:
    base = parse_document_to_text(path)
    best_candidates: list[str] = [base.full_text or ""]
    tables_plain: list[str] = []
    tables_html: list[str] = []
    images_texts: list[str] = []

    # Collect tables/images from parsed pages if present
    try:
        for page in base.pages or []:
            for el in page.get("elements", []) or []:
                if el.get("type") == "table_html":
                    tables_html.append(str(el.get("description") or ""))
                if el.get("type") == "image_ocr":
                    images_texts.append(str(el.get("description") or ""))
    except Exception:
        pass

    # For PDFs, try multiple text strategies and explicit table extraction
    if path.suffix.lower() == ".pdf":
        try:
            if pdf_text_plumber:
                best_candidates.append(pdf_text_plumber(path))
            if pdf_text_simple:
                best_candidates.append(pdf_text_simple(path))
            if pdf_text_ocr_pages:
                # As a last resort, limited OCR pages (respects parser limits)
                best_candidates.append(pdf_text_ocr_pages(path))
            if pdf_tables_rows:
                rows_list = pdf_tables_rows(path) or []
                for rows in rows_list:
                    # rows: list[list[str]]
                    try:
                        # Plain
                        plain = "\n".join(" | ".join(r) for r in rows)
                        if plain.strip():
                            tables_plain.append(plain)
                        # HTML
                        if render_html_table:
                            tables_html.append(render_html_table(rows))
                    except Exception:
                        continue
        except Exception:
            pass

    # Choose best main text
    best_text = choose_best_text(best_candidates)

    # Compose enriched reference text
    parts: list[str] = []
    if best_text:
        parts.append(best_text)
    if tables_plain:
        parts.append("\n\n---\nTables (plain):\n" + "\n\n".join(tables_plain))
    if images_texts:
        parts.append("\n\n---\nImages OCR extracts:\n" + "\n\n".join(images_texts))
    enriched_text = "\n\n".join(p for p in parts if p)

    reference = {
        "source_filename": path.name,
        "source_relpath": str(path),
        "expected_full_text": enriched_text,
        "elements": {
            "tables_html": tables_html,
            "tables_plain": tables_plain,
            "images_ocr": images_texts,
        },
        "notes": "Rich reference auto-generated from multi-pass parsing.",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "generated_by": "scripts/generate_references.py",
    }
    return reference


def main(args: list[str]) -> int:
    samples_dir = Path(args[0]) if args else ROOT / "data" / "samples"
    files = [p for p in samples_dir.rglob("*") if p.is_file() and not p.name.endswith(".reference")]
    if not files:
        print(f"No sample files found in {samples_dir}")
        return 0

    total = 0
    done = 0
    for f in files:
        total += 1
        try:
            ref = build_reference_for_file(f)
            out = f.with_name(f.name + ".reference")
            out.write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
            done += 1
            print(f"Saved reference: {out}")
        except Exception as e:
            print(f"Failed: {f} -> {e}")
    print(f"TOTAL={total} SAVED={done}")
    return 0 if done else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


