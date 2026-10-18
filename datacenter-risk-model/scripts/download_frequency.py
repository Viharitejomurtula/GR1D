"""Download Open Frequency Database files from OSF project by5hu (Rydin Gorjao et al., 2020).

Usage: download_frequency.py --list          # list FrequencyData files
       download_frequency.py <name-substring> # e.g. US / Texas
"""
import sys
from common import RAW, download, get_json, today, update_source

NODE = "https://api.osf.io/v2/nodes/by5hu/files/osfstorage/"


def listing(url):
    out = []
    while url:
        d = get_json(url)
        out += d["data"]
        url = d["links"].get("next")
    return out


def tree(url, prefix=""):
    for x in listing(url + ("&" if "?" in url else "?") + "page%5Bsize%5D=100"):
        a = x["attributes"]
        if a["kind"] == "folder":
            yield from tree(x["relationships"]["files"]["links"]["related"]["href"], prefix + a["name"] + "/")
        else:
            yield prefix + a["name"], x["links"]["download"], a.get("size")


def main(args):
    files = [f for f in tree(NODE) if f[0].startswith("FrequencyData/")]
    if args == ["--list"]:
        for n, _, s in files:
            print(n, s)
        return
    for n, url, _ in files:
        if any(a.lower() in n.lower() for a in args):
            print("downloading", n)
            download(url, RAW / "open_frequency_db" / n)
    update_source("F1a", url="https://osf.io/by5hu/", license="see OSF project (verify)",
                  version="OSF by5hu", download_date=today())


if __name__ == "__main__":
    main(sys.argv[1:] or ["--list"])
