"""Parse ERCOT monthly Operations Report docx files: 'Frequency Events' tables -> data/processed/ercot_frequency_events.csv.
Columns kept: datetime, delta_freq_hz (as reported; positive = under-frequency in the 2020 reports), max_min_freq_hz (nadir or peak), duration, mw_loss, load_mw,
wind_pct, inertia_gws, source file. Table layouts vary: columns are located by header text. Reports include events with dF >= 60 mHz, MW loss >= 350 MW or RRS deployment.
Usage: python -I parse_ercot_freq_events.py"""
import re
from pathlib import Path

import docx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/raw/ercot_ops_reports"
DT = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}")


def num(s):
    s = re.sub(r"[,%\s]", "", s.replace("−", "-"))
    try:
        return float(s)
    except ValueError:
        return None


rows, report = [], []
for f in sorted(SRC.glob("*.docx")):
    try:
        d = docx.Document(f)
    except Exception as e:
        report.append((f.name, "unreadable", str(e)[:60])); continue
    n0 = len(rows)
    for t in d.tables:
        hdr = " | ".join(c.text.strip().lower() for r in t.rows[:3] for c in r.cells)
        if "delta frequency" not in hdr and "max/min" not in hdr:
            continue
        # column map from first two rows combined
        ncol = len(t.rows[0].cells)
        names = [" ".join(t.rows[k].cells[j].text.strip().lower() for k in range(min(2, len(t.rows)))) for j in range(ncol)]
        def col(*keys):
            for j, n in enumerate(names):
                if all(k in n for k in keys):
                    return j
        c = dict(dt=0, df=col("delta", "freq") if col("delta", "freq") is not None else 1, mm=col("max/min"), dur=col("duration"),
                 mw=col("mw loss"), load=col("load"), wind=col("wind"), inertia=col("inertia"))
        for r in t.rows:
            cells = [x.text.strip() for x in r.cells]
            if not DT.match(cells[0]):
                continue
            g = lambda k: num(cells[c[k]]) if c.get(k) is not None and c[k] < len(cells) else None
            rows.append(dict(datetime=cells[0], delta_freq_hz=g("df"), max_min_freq_hz=g("mm"),
                             duration=cells[c["dur"]] if c.get("dur") is not None else None, mw_loss=g("mw"), load_mw=g("load"),
                             wind_pct=g("wind"), inertia_gws=g("inertia"), source=f.name))
    report.append((f.name, "events", len(rows) - n0))
E = pd.DataFrame(rows)
E["datetime"] = pd.to_datetime(E.datetime, errors="coerce", format="mixed")
E = E.dropna(subset=["datetime"]).sort_values(["datetime", "source"]).drop_duplicates(["datetime", "max_min_freq_hz"], keep="last")
E.to_csv(ROOT / "data/processed/ercot_frequency_events.csv", index=False)
print(pd.DataFrame(report, columns=["file", "kind", "n"]).to_string(index=False, max_colwidth=60))
print(len(E), "unique events", E.datetime.min(), E.datetime.max())
print(E.groupby(E.datetime.dt.year).size().to_dict())
