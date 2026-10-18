"""Minimal MAT5 reader (scipy.io unusable under numpy 2 here) for NASA EOS_DataSet.mat: numeric arrays aging_time, ESR, C."""
import struct, zlib, numpy as np

def _sub(b):
    off, out = 0, []
    while off + 8 <= len(b):
        t, n = struct.unpack('<II', b[off:off+8])
        if t >> 16: n, t, data, adv = t >> 16, t & 0xffff, b[off+4:off+4+(t >> 16)], 8
        else: data, adv = b[off+8:off+8+n], 8 + ((n + 7) // 8) * 8
        out.append((t, data)); off += adv
    return out

def load(path):
    b = open(path, 'rb').read(); off, res = 128, {}
    while off + 8 <= len(b):
        t, n = struct.unpack('<II', b[off:off+8]); body = b[off+8:off+8+n]; off += 8 + n   # compressed elements are unpadded
        if t == 15: body = zlib.decompress(body); body = body[8:]           # strip miMATRIX tag
        e = _sub(body)
        dims = struct.unpack(f'<{len(e[1][1])//4}i', e[1][1]); name = e[2][1].decode()
        dt = {1: '<i1', 2: '<u1', 3: '<i2', 4: '<u2', 5: '<i4', 6: '<u4', 9: '<f8'}[e[3][0]]
        res[name] = np.frombuffer(e[3][1], dt).astype(float).reshape(dims, order='F')
    return res

if __name__ == "__main__":
    import sys
    for k, v in load(sys.argv[1]).items(): print(k, v.shape, v.ravel()[:6])
