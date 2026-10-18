"""Generate a surrogate training dataset from the actual simulator, in parallel shards, then merge.

What this file is
    Runs surrogate.data.generate() in K parallel shards on one machine. Each shard works in its own copy
    of the repo (its own build/ folder: the simulator's runner writes fixed file names there, so shards
    sharing one folder would overwrite each other) and generates its share in chunks, so per-run traces
    (~22 MB each, kept until a chunk is graded) never pile up on disk. Every chunk has its own seed and
    its own output file, named before any work starts; a re-run skips chunks whose CSV and provenance
    already exist (resume after an interruption). Finally all chunks are merged with surrogate.data.merge().

Scope
    By default every scenario's dip retains C.VALID_DIP_DEPTH_PU (0.70-0.90 pu; ~69% of real sags): the simulator is
    only trusted there (the deep-sag voltage-collapse problem is open, see validation/CROSSCHECK.md), so the surrogate
    must not be trained outside it. --full-depth-range opts out (full Eaton/EPRI 0-0.9 pu distribution). The scope is
    written into every chunk's provenance and the merged provenance ("scope"), and a resume refuses to mix scopes.

Usage (from the repo root, with the venv's python and the simulator available):
    .env/bin/python scripts/generate_dataset.py --label full --n 20000 --shards 32 --chunk 200 --seed0 1

Inputs: --label (output name), --n (total runs), --shards, --chunk (runs per generate() call), --seed0
    (chunk j of shard k uses seed seed0 + 1000*k + j), --out (data folder), --shard-root (repo copies).
Outputs: <out>/<label>_chunks/s<k>_seed<seed>.csv (+ .provenance.json), one log per shard
    (<out>/<label>_chunks/shard<k>.log), and the merged <out>/<label>.csv (+ provenance, incl. "scope").
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))       # run as a script from scripts/: make sim and surrogate importable
from sim import constants as C   # noqa: E402

COPY_EXCLUDES = [".env/", "frontend/", "data_bayesian-network/drivers_raw/", "*_res.csv", "__pycache__/", ".pytest_cache/"]


def plan(n: int, shards: int, chunk: int, seed0: int, chunk_dir: Path) -> list[list[tuple[int, int, str]]]:
    """Per shard, its chunks as (runs, seed, csv path). Shard k gets n // shards runs (+1 for the first
    n % shards); empty shards get no chunks. Seeds are seed0 + 1000*k + j, so all chunks differ."""
    out = []
    for k in range(shards):
        todo, j, chunks = n // shards + (1 if k < n % shards else 0), 0, []
        while todo > 0:
            m = min(chunk, todo)
            seed = seed0 + 1000 * k + j
            chunks.append((m, seed, str(chunk_dir / f"s{k + 1:02d}_seed{seed}.csv")))
            todo -= m
            j += 1
        out.append(chunks)
    return out


def prepare_copies(shards: int, shard_root: Path) -> list[Path]:
    """One repo copy per shard (rsync, so repeat runs only refresh changed files), compiled simulator included."""
    from sim import runner
    runner.build()                                   # compile once here; the copies reuse the executable
    dirs = []
    for k in range(shards):
        d = shard_root / f"s{k + 1:02d}"
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run(["rsync", "-a", "--delete", *[f"--exclude={e}" for e in COPY_EXCLUDES], f"{REPO}/", f"{d}/"], check=True)
        dirs.append(d)
    return dirs


def scope_record(in_scope_only: bool) -> dict:
    """The scope written into provenance: which dip depths the scenarios were drawn from."""
    if in_scope_only:
        return {"in_scope_only": True, "dip_depth_pu": list(C.VALID_DIP_DEPTH_PU), "share_of_sags": C.IN_SCOPE_SAG_SHARE,
                "note": "Eaton/EPRI depth distribution conditioned on the simulator's valid band"}
    return {"in_scope_only": False, "dip_depth_pu": [0.0, 0.9], "share_of_sags": 1.0,
            "note": f"full Eaton/EPRI depth distribution; includes sags outside the valid band {list(C.VALID_DIP_DEPTH_PU)}"}


# sim.scenario.DEFAULT_IN_SCOPE_ONLY is set before generate() runs: generate() -> sim.batch.run_batch -> sample_many(n, seed)
# takes no scope argument, and the module default is read at call time.
SHARD_CODE = """
import json, sys, time
from pathlib import Path
import sim.scenario
from surrogate.data import generate, provenance_path
chunks, scope, t0, done = json.loads(sys.argv[1]), json.loads(sys.argv[2]), time.time(), 0
sim.scenario.DEFAULT_IN_SCOPE_ONLY = scope["in_scope_only"]
total = sum(m for m, _, _ in chunks)
for m, seed, path in chunks:
    if Path(path).exists() and provenance_path(path).exists():
        old = json.loads(provenance_path(path).read_text()).get("scope", {}).get("in_scope_only")
        if old != scope["in_scope_only"]:
            sys.exit(f"{Path(path).name} exists with scope in_scope_only={old}, this run wants {scope['in_scope_only']}: use another --label")
        done += m; print(f"skip {Path(path).name} (exists)", flush=True); continue
    generate(m, seed, path)
    prov = provenance_path(path)
    prov.write_text(json.dumps(json.loads(prov.read_text()) | {"scope": scope}, indent=2))
    done += m
    print(f"chunk seed {seed}: {done}/{total} runs, {time.time() - t0:.0f}s", flush=True)
print("SHARD DONE", flush=True)
"""


def main(argv: list[str] | None = None) -> int:
    """Run the shards, wait, check every chunk exists, merge. Exit code 0 only if all of that succeeded."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--label", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--shards", type=int, default=os.cpu_count())
    ap.add_argument("--chunk", type=int, default=200)
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--out", default="/root/data")
    ap.add_argument("--shard-root", default="/root/shards")
    ap.add_argument("--full-depth-range", action="store_true",
                    help=f"opt out of the valid band {C.VALID_DIP_DEPTH_PU} pu and sample the full 0-0.9 pu depth "
                         "distribution (includes deep sags the simulator is not trusted for)")
    a = ap.parse_args(argv)
    scope = scope_record(not a.full_depth_range)

    out, chunk_dir = Path(a.out), Path(a.out) / f"{a.label}_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    work = plan(a.n, a.shards, a.chunk, a.seed0, chunk_dir)
    dirs = prepare_copies(a.shards, Path(a.shard_root))
    print(f"{a.label}: {a.n} runs, {sum(1 for w in work if w)} active shards, {sum(len(w) for w in work)} chunks; "
          f"dip depth scope {scope['dip_depth_pu']} pu", flush=True)

    t0, procs = time.time(), []
    for k, (chunks, d) in enumerate(zip(work, dirs)):
        if not chunks:
            continue
        log = open(chunk_dir / f"shard{k + 1:02d}.log", "a")
        env = {**os.environ, "PYTHONPATH": str(d), "PYTHONDONTWRITEBYTECODE": "1"}
        procs.append((k + 1, subprocess.Popen([sys.executable, "-c", SHARD_CODE, json.dumps(chunks), json.dumps(scope)], cwd=d, env=env,
                                              stdout=log, stderr=subprocess.STDOUT)))
    codes = {k: p.wait() for k, p in procs}
    wall = time.time() - t0
    print(f"shards finished in {wall:.0f}s; exit codes {codes}", flush=True)

    paths = [p for w in work for _, _, p in w]
    missing = [p for p in paths if not Path(p).exists()]
    if any(codes.values()) or missing:
        print(f"FAILED: {len(missing)} chunk files missing; see {chunk_dir}/shard*.log", flush=True)
        return 1
    from surrogate.data import merge
    merged = merge(paths, out / f"{a.label}.csv")
    from surrogate.data import provenance_path
    prov = provenance_path(merged)
    prov.write_text(json.dumps(json.loads(prov.read_text()) | {"scope": scope}, indent=2))
    (chunk_dir / "timing.json").write_text(json.dumps({"n": a.n, "shards": a.shards, "chunk": a.chunk, "wall_s": wall, "scope": scope}))
    print(f"merged {len(paths)} chunks -> {merged} in {wall:.0f}s ({a.n / wall:.1f} runs/s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
