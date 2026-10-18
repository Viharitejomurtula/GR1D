"""Download ERCOT monthly 'Operations Report' (docx; frequency event tables) from ROS meeting pages.
ROS year page -> meeting calendar pages -> hrefs matching Operations_Report. Writes data/raw/ercot_ops_reports/<name>.docx and index.csv
Usage: python download_ercot_ops_reports.py 2019 2020 ..."""
import csv
import re
import sys
import time
import urllib.parse
import urllib.request

from common import RAW, download

OUT = RAW / "ercot_ops_reports"
HOST = "https://www.ercot.com"


def fetch(url, tries=8):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"retry {i + 1} {url}: {e}"); time.sleep(3)
    return ""


def main(years):
    OUT.mkdir(parents=True, exist_ok=True)
    idx = OUT / "index.csv"
    seen = {r["url"] for r in csv.DictReader(open(idx))} if idx.exists() else set()
    rows = []
    for y in years:
        page = fetch(f"{HOST}/committees/ros/{y}")
        meetings = sorted(set(re.findall(r'/calendar/\d{8}-ROS[-\w]*', page)))
        print(y, len(meetings), "ROS calendar entries")
        for m in meetings:
            html = fetch(HOST + m)
            for href in set(re.findall(r'href="([^"]*[Oo]perations[_%20 -]*Report[^"]*\.docx?)"', html, re.I)):
                url = urllib.parse.urljoin(HOST, href)
                if url in seen:
                    continue
                name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
                try:
                    download(url, OUT / name); seen.add(url); rows.append((m, url, name)); print("got", name)
                except Exception as e:
                    print("failed", url, e)
    new = not idx.exists()
    with open(idx, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["meeting", "url", "file"])
        w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:] or ["2019", "2020", "2021", "2022", "2023"])
