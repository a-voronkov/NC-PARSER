import sys
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

# Ensure package import
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nc_parser.processing.parser import parse_document_to_text  # noqa: E402


def load_reference(path: Path) -> dict:
    # Support BOM if present
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalize_text(s: str) -> str:
    if s is None:
        return ""
    s2 = s.replace("\ufeff", "").replace("\r", "").replace("\xa0", " ")
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def compare_texts(expected: str, got: str) -> dict:
    e_raw = expected or ""
    g_raw = got or ""
    e = _normalize_text(e_raw)
    g = _normalize_text(g_raw)
    ratio = SequenceMatcher(None, e, g).ratio() if (e or g) else 1.0
    exp_len = len(e)
    got_len = len(g)
    if ratio >= 0.98:
        verdict = "match"
    elif ratio >= 0.90:
        verdict = "close"
    elif got_len > exp_len and ratio >= 0.85:
        verdict = "likely_better_more_text"
    elif got_len < exp_len and ratio < 0.70:
        verdict = "likely_worse_less_text"
    else:
        verdict = "different"
    return {"equal": e == g, "ratio": ratio, "exp_len": exp_len, "got_len": got_len, "verdict": verdict}


def main(args: list[str]) -> int:
    # If specific .reference files passed, use them; otherwise scan dir
    if args and any(a.endswith(".reference") for a in args):
        refs = [Path(a) for a in args if a.endswith(".reference")]
    else:
        samples_dir = Path(args[0]) if args else ROOT / "data" / "samples"
        refs = list(samples_dir.rglob("*.reference"))
    if not refs:
        print(f"No .reference files found under {samples_dir}")
        return 0

    total = 0
    ok = 0
    fail = 0
    for rf in refs:
        total += 1
        try:
            ref = load_reference(rf)
            source = rf.with_name(ref["source_filename"])  # same folder
            if not source.exists():
                raise FileNotFoundError(f"source not found: {source}")
            parsed = parse_document_to_text(source)
            cmp = compare_texts(ref.get("expected_full_text", ""), parsed.full_text)
            if cmp["equal"]:
                ok += 1
            else:
                fail += 1
            print(
                f"{('OK  ' if cmp['equal'] else 'DIFF')}: {source.name} "
                f"verdict={cmp['verdict']} ratio={cmp['ratio']:.3f} exp_len={cmp['exp_len']} got_len={cmp['got_len']}"
            )
            diff = source.with_suffix(source.suffix + ".diff.txt")
            got = (_normalize_text(parsed.full_text or ""))[:1200]
            exp = (_normalize_text(ref.get("expected_full_text", "") or ""))[:1200]
            diff.write_text(f"EXPECTED:\n{exp}\n\nGOT:\n{got}", encoding="utf-8")
        except Exception as e:
            fail += 1
            print(f"ERR : {rf.name} -> {e}")

    print(f"TOTAL={total} OK={ok} FAIL={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


