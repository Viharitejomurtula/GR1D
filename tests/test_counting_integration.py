"""Integration tests: need the compiled Modelica model (docker + OpenModelica). Skipped unless OM_IMAGE is set.
Run: OM_IMAGE=openmodelica/openmodelica:v1.25.0-minimal python3 -m pytest tests/test_counting_integration.py"""
import os
from dataclasses import replace
import numpy as np, pytest
from sim import runner, scenario as S

pytestmark = pytest.mark.skipif(not os.environ.get("OM_IMAGE") and not os.environ.get("GR1D_NATIVE"), reason="OpenModelica toolchain not configured")

def _seq(gaps, dur=0.05, depth=0.5, **kw):
    base = replace(S.GRID_FRIENDLY, dip_duration_s=dur, dip_depth_pu=depth, count_n=3, count_window_s=60.0, **kw)
    return replace(base, extra_dips=tuple((g, dur, depth) for g in gaps))

def _latched(sc, tag):
    runner.run(sc, tag=tag); d = runner._read_csv(runner.BUILD / f"{tag}_res.csv"); return bool(d["count_transfer"].max() > 0.5), d

def test_three_dips_in_window_latch_transfer():
    ok, d = _latched(_seq([10.0, 10.0]), "t3in"); assert ok
    assert d["p_grid_w"][-1] < 0.5 * d["p_grid_w"][d["time"] < 1.0].mean()      # stays off: load did not return

def test_two_dips_do_not_latch():
    ok, _ = _latched(_seq([10.0]), "t2"); assert not ok

def test_third_dip_outside_window_does_not_latch():
    ok, _ = _latched(_seq([40.0, 40.0]), "tout"); assert not ok   # first dip has aged out of the 60 s window by the third

def test_lengthened_counting_timer_ignores_short_sags():
    # sags last ~0.17 s below 0.90 pu (dip + recovery tail); a 0.5 s minimum means none is counted
    ok, _ = _latched(_seq([10.0, 10.0], count_min_dur_s=0.5), "tlen"); assert not ok
