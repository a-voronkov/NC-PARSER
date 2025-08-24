import sys
from pathlib import Path

# Ensure local package import works when running from repo root
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nc_parser.processing.parser import parse_document_to_text  # noqa: E402


def main(args: list[str]) -> int:
    # Default small samples if none provided
    if not args:
        args = [
            "data/samples/book.txt",
            "data/samples/account_activities_202508.csv",
        ]

    for p in args:
        path = Path(p)
        if not path.exists():
            print(f"MISSING: {path}")
            continue
        doc = parse_document_to_text(path)
        text = doc.full_text or ""
        snippet = text[:400].replace("\n", " ")
        print(f"FILE: {path} | chars={len(text)} | pages={len(doc.pages)}")
        print(f"SNIPPET: {snippet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


