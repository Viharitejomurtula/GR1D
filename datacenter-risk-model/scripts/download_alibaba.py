"""Alibaba ASI GPU trace v2026 (OSDI'26): download job execution summary; range-extract a SAMPLE of hourly pod partitions
from the 352 GB pod_hourly zip via HTTP range requests (central directory + selected members only).

Usage: python download_alibaba.py summary
       python download_alibaba.py pods <day,day,...>   (all 24 hours of each listed day)
"""
import io
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from common import RAW, download, today, update_source

BASE = "https://tre-clusterdata.oss-cn-hangzhou.aliyuncs.com/cluster-trace-gpu-v2026/data"


class RangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests with retries."""

    def __init__(self, url, size, block=1 << 20):
        self.url, self.size, self.pos, self.block = url, size, 0, block
        self.cache = {}

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def _fetch(self, a, b):
        for i in range(12):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={a}-{b}"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.read()
            except Exception as e:
                print(f"retry {i + 1}: {e}")
                time.sleep(3)
        raise RuntimeError("range fetch failed")

    def readinto(self, buf):
        n = min(len(buf), self.size - self.pos)
        if n <= 0:
            return 0
        data = self._fetch(self.pos, self.pos + n - 1)
        buf[:len(data)] = data
        self.pos += len(data)
        return len(data)


def main(args):
    if args[0] == "summary":
        download(f"{BASE}/asi_opensource_job_execution_summary.zip", RAW / "alibaba_2026" / "job_execution_summary.zip")
        update_source("F2c", url="https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2026", license="see repo (verify)",
                      version="cluster-trace-gpu-v2026", download_date=today())
        return
    days = {int(d) for d in args[1].split(",")}
    url = f"{BASE}/asi_opensource_pod_hourly.zip"
    for i in range(12):
        try:
            size = int(urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60).headers["Content-Length"])
            break
        except Exception as e:
            print(f"retry {i + 1}: {e}")
            time.sleep(3)
    z = zipfile.ZipFile(io.BufferedReader(RangeFile(url, size), buffer_size=1 << 20))
    names = [n for n in z.namelist() if n.endswith(".parquet") and (m := re.search(r"day=(\d+)/", n)) and int(m.group(1)) in days]
    print(len(z.namelist()), "members; extracting", len(names))
    out = RAW / "alibaba_2026" / "pod_hourly_sample"
    for n in names:
        dest = out / n
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        with z.open(n) as src, open(tmp, "wb") as f:
            f.write(src.read())
        tmp.rename(dest)
        print("got", n, dest.stat().st_size)


if __name__ == "__main__":
    main(sys.argv[1:])
