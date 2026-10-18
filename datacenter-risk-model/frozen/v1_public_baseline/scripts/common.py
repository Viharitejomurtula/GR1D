"""Shared download helpers: retrying, resumable fetch and sources.csv logging."""
import csv
import datetime as dt
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def get_json(url: str, tries: int = 6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # DNS/network flakiness
            print(f"retry {i + 1}/{tries} {url}: {e}")
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed: {url}")


def download(url: str, dest: Path, tries: int = 20) -> Path:
    """Resumable download via HTTP Range; safe to rerun."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for i in range(tries):
        have = dest.stat().st_size if dest.exists() else 0
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status == 200 and have:  # server ignored Range
                    have = 0
                with open(dest, "ab" if have else "wb") as f:
                    while chunk := r.read(1 << 20):
                        f.write(chunk)
            return dest
        except urllib.error.HTTPError as e:
            if e.code == 416:  # already complete
                return dest
            print(f"retry {i + 1}/{tries}: {e}")
        except Exception as e:
            print(f"retry {i + 1}/{tries}: {e}")
        time.sleep(3)
    raise RuntimeError(f"failed: {url}")


def update_source(row_id: str, **fields):
    """Fill blank/updated fields of a sources.csv row (e.g. url, download_date)."""
    path = ROOT / "sources.csv"
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        if r["id"] == row_id:
            r.update(fields)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def today() -> str:
    return dt.date.today().isoformat()
