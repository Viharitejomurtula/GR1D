"""Extract complete members from a (possibly partially downloaded) zip by parsing local headers sequentially.
Usage: python extract_partial_zip.py <zip> <out_dir>   (skips members already extracted; stops at the first incomplete member)"""
import os
import struct
import sys
import zlib

path, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
f = open(path, "rb"); size = os.path.getsize(path); off = 0
while True:
    f.seek(off); h = f.read(30)
    if h[:4] != b"PK\x03\x04":
        print("no more local headers at", off); break
    _, flag, method, _, _, crc, csz, usz, nl, el = struct.unpack("<HHHHHIIIHH", h[4:30])
    name = f.read(nl).decode(); extra = f.read(el)
    if csz == 0xFFFFFFFF or usz == 0xFFFFFFFF:
        i = 0
        while i < len(extra):
            tag, l = struct.unpack("<HH", extra[i:i + 4])
            if tag == 1:
                usz, csz = struct.unpack("<QQ", extra[i + 4:i + 20])
            i += 4 + l
    data0 = f.tell(); end = data0 + csz
    if name.endswith("/"):
        off = end; continue
    out = os.path.join(outdir, os.path.basename(name))
    if end > size:
        print("incomplete:", name, f"have {size - data0} of {csz}"); break
    if os.path.exists(out) and os.path.getsize(out) == usz:
        print("already", name); off = end; continue
    f.seek(data0); dec = zlib.decompressobj(-15) if method == 8 else None; c = 0; left = csz
    with open(out, "wb") as o:
        while left > 0:
            b = f.read(min(1 << 22, left)); left -= len(b)
            b = dec.decompress(b) if dec else b
            c = zlib.crc32(b, c); o.write(b)
    print("extracted", out, "crc ok" if c == crc else "CRC MISMATCH")
    off = end
