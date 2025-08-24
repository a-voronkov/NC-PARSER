import sys
import json
from pathlib import Path

# ensure package path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nc_parser.processing.parser import parse_document_to_text  # noqa: E402


def main(args: list[str]) -> int:
    if not args:
        print("Usage: python scripts/single_to_reference.py <path-to-sample-file>")
        return 1
    path = Path(args[0]).resolve()
    if not path.exists():
        print(f"Missing: {path}")
        return 1
    doc = parse_document_to_text(path)
    ref = {
        "source_filename": path.name,
        "source_relpath": str(path),
        "expected_full_text": doc.full_text or "",
        "notes": "Gold reference from current offline parser output.",
        "generated_at": "",  # keep minimal to avoid churn
    }
    out = Path(f"{str(path)}.reference")
    out.write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


