"""Download NOAA GHCNh hourly records for ERCOT-area stations (Austin, Dallas-Fort Worth)."""
import sys
from common import RAW, download, today, update_source

BASE = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly"
STATIONS = {"USW00013904": "KAUS Austin-Bergstrom", "USW00003927": "KDFW Dallas-Fort Worth"}


def main(ids=None):
    for sid in ids or STATIONS:
        url = f"{BASE}/access/by-station/GHCNh_{sid}_por.psv"
        print("downloading", sid, STATIONS.get(sid, ""))
        download(url, RAW / "ghcnh" / f"GHCNh_{sid}_por.psv")
    update_source("F1c", url=BASE, license="Public domain (NOAA NCEI)",
                  version="GHCNh por files", download_date=today())


if __name__ == "__main__":
    main(sys.argv[1:] or None)
