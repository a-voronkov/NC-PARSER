import sys
import json
import time
import re
from difflib import SequenceMatcher
from pathlib import Path

import requests


def _normalize_text(s: str) -> str:
    if s is None:
        return ""
    s2 = s.replace("\ufeff", "").replace("\r", "").replace("\xa0", " ")
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def _compare(expected: str, got: str) -> dict:
    e = _normalize_text(expected or "")
    g = _normalize_text(got or "")
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


def _upload_file(base_url: str, path: Path) -> str:
    with path.open("rb") as f:
        resp = requests.post(f"{base_url}/upload", files={"file": (path.name, f, "application/octet-stream")}, timeout=120)
    resp.raise_for_status()
    return resp.json()["file_id"]


def _poll_result(base_url: str, file_id: str, timeout_sec: int = 180) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            res = requests.get(f"{base_url}/result/{file_id}", timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError(f"Result not ready for {file_id}")


def main(args: list[str]) -> int:
    base_url = args[0] if args else "http://localhost:8080"
    samples_dir = Path(args[1]) if len(args) > 1 else Path("data/samples")

    refs = list(samples_dir.rglob("*.reference"))
    if not refs:
        print(f"No .reference under {samples_dir}")
        return 0

    total = 0
    ok = 0
    diff = 0
    for rf in refs:
        total += 1
        try:
            ref = json.loads(rf.read_text(encoding="utf-8"))
        except Exception:
            ref = json.loads(rf.read_text(encoding="utf-8-sig"))
        source = rf.with_name(ref["source_filename"])
        if not source.exists():
            print(f"ERR : {rf.name} -> source missing {source.name}")
            diff += 1
            continue
        try:
            file_id = _upload_file(base_url, source)
            result = _poll_result(base_url, file_id, timeout_sec=240)
            got_text = result.get("full_text", "")
            cmp = _compare(ref.get("expected_full_text", ""), got_text)
            tag = "OK  " if cmp["equal"] else "DIFF"
            if cmp["equal"]:
                ok += 1
            else:
                diff += 1
            print(
                f"{tag}: {source.name} verdict={cmp['verdict']} ratio={cmp['ratio']:.3f} "
                f"exp_len={cmp['exp_len']} got_len={cmp['got_len']}"
            )
            # brief diff
            out = source.with_suffix(source.suffix + ".api.diff.txt")
            exp = _normalize_text(ref.get("expected_full_text", ""))[:1200]
            got = _normalize_text(got_text)[:1200]
            out.write_text(f"EXPECTED:\n{exp}\n\nGOT:\n{got}", encoding="utf-8")
        except Exception as e:
            print(f"ERR : {source.name} -> {e}")
            diff += 1
    print(f"TOTAL={total} OK={ok} DIFF={diff}")
    return 0 if diff == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


