"""Tests for the surrogate package, on real simulator output only.

What this file is
    Checks the encoder, data loading, model shapes, large-batch prediction, ONNX parity and a 3-epoch
    training smoke run. Data: scenarios from sim.scenario.sample_many (inputs) and data/runs.csv
    (simulator outputs; no test asserts accuracy). data/runs.csv predates the simulator structure fixes
    and lacks 16 of today's inputs, so it is used only for output-side checks (filters, split, target
    scaling); training tests run on SURROGATE_DATASET when that points at a CSV from the current
    simulator (surrogate.data.generate) and are skipped otherwise. Tests that need OpenModelica
    (generate, verify) are skipped with the reason when it is unavailable.

Reads (read-only): data/runs.csv.
Writes: only pytest's tmp_path (model directories, ONNX files).
"""
from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd
import pytest
import torch

from sim import scenario
from surrogate import data as sdata
from surrogate import export, train, verify
from surrogate.features import CATEGORICAL, FeatureEncoder, _reaches_runner, excluded_fields
from surrogate.model import HEADS, Ensemble
from surrogate.predict import Surrogate

RUNS = sdata.REPO_ROOT / "data" / "runs.csv"
SIM_OK, SIM_WHY = sdata.simulator_available()
needs_sim = pytest.mark.skipif(not SIM_OK, reason=f"needs the actual simulator (OpenModelica): {SIM_WHY}")
CURRENT = os.environ.get("SURROGATE_DATASET") or (str(RUNS) if not sdata.missing_inputs(RUNS) else "")
needs_current_data = pytest.mark.skipif(
    not CURRENT, reason="no dataset from the current simulator: data/runs.csv lacks "
    f"{len(sdata.missing_inputs(RUNS))} current inputs; generate one with surrogate.data.generate and set SURROGATE_DATASET")


@pytest.fixture(scope="module")
def loaded():
    """data.load(data/runs.csv, require_inputs=False) -> (frame, report): outputs only."""
    return sdata.load(RUNS, require_inputs=False)


@pytest.fixture(scope="module")
def encoder(loaded) -> FeatureEncoder:
    """For mechanics tests: input statistics from 5,000 sample_many scenarios (today's inputs), target
    scaling and classes from data/runs.csv outputs. Not a trained model's encoder."""
    d, _ = loaded
    scs = pd.DataFrame([s.to_vector() for s in scenario.sample_many(5_000, seed=10)], columns=list(scenario.FIELD_ORDER))
    return FeatureEncoder().fit_inputs(scs).fit_targets(d, classes=sorted(d["failure_mode"].unique()))


def test_excluded_fields_are_those_the_runner_never_sends():
    """Since the structure fixes every sampled input reaches the model (the runner sends PARAM_MAP,
    INT_PARAMS and the fields it encodes itself: z_total_pct, the dip sequence, the group arrays, the
    VFD flag), so none is excluded; the encoder drops only the constant dip_start_s. Each field's
    effect is checked on many scenarios because some act only conditionally."""
    assert excluded_fields() == []
    sc = next(s for s in scenario.sample_many(200, seed=0) if s.second_dip and s.n_groups > 1)
    for f in ("reclose_gap_s", "grp_load_cv"):                      # conditional fields really are sent
        assert _reaches_runner(sc, f)


def test_encoder_round_trips_on_sampled_scenarios(encoder, tmp_path):
    """save/load gives an identical encoder and identical features on sample_many scenarios."""
    encoder.save(tmp_path / "enc.json")
    again = FeatureEncoder.load(tmp_path / "enc.json")
    scs = scenario.sample_many(500, seed=11)
    np.testing.assert_array_equal(encoder.transform(scs), again.transform(scs))
    assert again.__dict__ == encoder.__dict__
    assert encoder.excluded == ["dip_start_s"] and "dip_start_s" not in encoder.feature_names()
    assert set(encoder.categories) == set(CATEGORICAL)


def test_load_refuses_a_dataset_from_an_older_simulator():
    """data/runs.csv lacks inputs the current Scenario has, so load() refuses it by default and names them."""
    gone = sdata.missing_inputs(RUNS)
    assert gone and "chain_loading_frac" in gone
    with pytest.raises(ValueError, match="predates the current simulator"):
        sdata.load(RUNS)


def test_load_drops_crash_rows_and_flags_censored(loaded, capsys):
    """data/runs.csv outputs: 77 'no disturbance' rows with dip_depth_pu < 0.9 dropped and reported (the
    file has no numerics_ok column, so nothing is dropped for numerics)."""
    d, rep = loaded
    print("data.load(data/runs.csv, require_inputs=False):", rep)
    assert rep["rows_read"] == 2000 and rep["dropped_crash"] == 77 and rep["dropped_numerics"] == 0
    assert rep["kept"] == 2000 - 77 - rep["dropped_non_finite"]
    assert not ((d["failure_mode"] == "no disturbance") & (d["dip_depth_pu"] < 0.9)).any()
    expected = (d["recovery_margin_s"] < 0) & (d["final_power_frac"] < 0.9)
    assert (d["censored"] == expected).all() and rep["censored"] == int(expected.sum()) > 0


def test_model_output_shapes(encoder):
    """Each member returns one value per row for every scalar head and n_classes failure_mode logits."""
    ens = Ensemble.create(encoder, seed=0)
    x = torch.as_tensor(encoder.transform(scenario.sample_many(64, seed=12)))
    out = ens.members[0](x)
    for h in HEADS:
        assert out[h].shape == (64,)
    assert out["failure_mode"].shape == (64, len(encoder.classes))
    assert ens.members[0].forward_flat(x).shape == (64, len(HEADS) + len(encoder.classes))


def test_predict_one_million_sampled_scenarios(encoder):
    """Ensemble predictions for 1,000,000 sample_many scenarios are finite, batched."""
    scs = scenario.sample_many(1_000_000, seed=13)
    frame = pd.DataFrame(np.array([s.to_vector() for s in scs]), columns=list(scenario.FIELD_ORDER))
    pred = Surrogate(Ensemble.create(encoder, seed=0)).predict(frame)
    assert len(pred) == 1_000_000 and np.isfinite(pred.select_dtypes("number").to_numpy()).all()


def test_onnx_parity(encoder, tmp_path, capsys):
    """Every exported member matches PyTorch within CONFIG['onnx_parity_atol'] on sample_many scenarios."""
    ens = Ensemble.create(encoder, seed=0)
    res = export.parity(ens, export.export(ens, tmp_path), scenario.sample_many(2_000, seed=14))
    with capsys.disabled():
        print(f"\nONNX parity: max |PyTorch - ONNX| per member {['%.2e' % d for d in res['max_abs_diff']]}, "
              f"atol {res['atol']:g}, rows {res['n_rows']}, passed {res['passed']}")
    assert res["passed"]


@needs_current_data
def test_smoke_train_three_epochs(tmp_path, capsys):
    """3 epochs on a dataset from the current simulator: the pipeline runs end to end and writes every artifact."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                 # provenance warnings are reported in res["warnings"]
        res = train.train(CURRENT, tmp_path, seed=0, overrides={"max_epochs": 3})
    with capsys.disabled():
        print("\nSMOKE TEST ONLY: simulator labels known to be wrong; metrics not meaningful")
        print("  data:", res["data"])
        print("  member epochs:", [m["epochs"] for m in res["members"]])
        print("  warnings:", res["warnings"])
        print("  std_scale:", {k: round(v, 3) for k, v in res["std_scale"].items()})
        print("  test:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res["test"].items()})
    for f in ["encoder.json", "config.json", "provenance.json", "split.json", "calibration.json", "metrics.json"] + [f"member_{i}.pt" for i in range(5)]:
        assert (tmp_path / f).exists(), f
    pred = Surrogate.load(tmp_path).predict(scenario.sample_many(100, seed=15))
    assert len(pred) == 100


@needs_current_data
def test_training_is_reproducible(tmp_path):
    """The same seed gives identical member weights and metrics (2 epochs)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        a = train.train(CURRENT, tmp_path / "a", seed=4, overrides={"max_epochs": 2})
        b = train.train(CURRENT, tmp_path / "b", seed=4, overrides={"max_epochs": 2})
    assert a["test"] == b["test"]
    for i in range(5):
        wa = torch.load(tmp_path / "a" / f"member_{i}.pt", weights_only=True)
        wb = torch.load(tmp_path / "b" / f"member_{i}.pt", weights_only=True)
        assert all(torch.equal(wa[k], wb[k]) for k in wa)


def test_split_reaches_every_failure_mode(loaded):
    """Stratifying on passed x failure_mode puts every failure mode with >= 3 rows in val and test,
    and keeps the passed share equal across splits (within 0.02)."""
    d, _ = loaded
    split = train.stratified_split(train.strata(d), {"train": 0.7, "val": 0.15, "test": 0.15}, 0)
    assert sum(len(v) for v in split.values()) == len(d) and len(np.unique(np.concatenate(list(split.values())))) == len(d)
    for mode, n in d["failure_mode"].value_counts().items():
        if n >= 3:
            for k in ("val", "test"):
                assert (d.iloc[split[k]]["failure_mode"] == mode).any(), (mode, k)
    shares = [d.iloc[split[k]]["passed"].mean() for k in ("train", "val", "test")]
    assert max(shares) - min(shares) < 0.02


def test_std_scale_multiplies_regression_std(encoder):
    """An ensemble's std_scale multiplies each regression std and leaves means and P(pass) unchanged."""
    x = encoder.transform(scenario.sample_many(200, seed=16))
    base = Ensemble.create(encoder, seed=0)
    scaled = Ensemble(base.members, encoder, {"recovery_margin_s": 2.0, "min_power": 0.5})
    a, b = base.predict(x), scaled.predict(x)
    np.testing.assert_allclose(b["recovery_margin_s_std"], 2.0 * a["recovery_margin_s_std"], rtol=1e-6)
    np.testing.assert_allclose(b["min_power_std"], 0.5 * a["min_power_std"], rtol=1e-6)
    np.testing.assert_array_equal(b["peak_current_pu_std"], a["peak_current_pu_std"])
    np.testing.assert_array_equal(b["recovery_margin_s_mean"], a["recovery_margin_s_mean"])
    np.testing.assert_array_equal(b["p_pass_mean"], a["p_pass_mean"])


def test_generate_refuses_data_runs_csv():
    """generate() never writes data/runs.csv (checked before the simulator is touched)."""
    with pytest.raises(ValueError):
        sdata.generate(1, 0, RUNS)


def test_merge_refuses_files_without_provenance(tmp_path):
    """merge() only accepts generate() output: data/runs.csv has no provenance file."""
    with pytest.raises(ValueError, match="no provenance"):
        sdata.merge([RUNS], tmp_path / "m.csv")
    with pytest.raises(ValueError):
        sdata.merge([RUNS], RUNS)


@needs_sim
def test_generate_shards_and_merge(tmp_path):
    """Two 2-run shards from the actual simulator merge into one 4-row dataset with both seeds recorded."""
    a = sdata.generate(2, 301, tmp_path / "a.csv")
    b = sdata.generate(2, 302, tmp_path / "b.csv")
    m = sdata.merge([a, b], tmp_path / "m.csv")
    prov = sdata.read_provenance(m)
    assert prov["seeds"] == [301, 302] and prov["n"] == len(pd.read_csv(m))
    with pytest.raises(ValueError, match="duplicate seeds"):
        sdata.merge([a, a], tmp_path / "dup.csv")


@needs_sim
def test_generate_runs_the_simulator(tmp_path):
    """A 3-run dataset from the actual simulator loads and carries provenance."""
    csv = sdata.generate(3, 101, tmp_path / "gen.csv")
    d, rep = sdata.load(csv)
    assert rep["rows_read"] == 3 and sdata.read_provenance(csv)["simulator_commit"]


@needs_sim
def test_verify_against_the_simulator(tmp_path):
    """verify() runs new scenarios through the simulator and the surrogate (labels from data/runs.csv,
    so only the mechanics are checked)."""
    csv = sdata.generate(30, 201, tmp_path / "gen.csv")
    train.train(csv, tmp_path / "m", seed=0, overrides={"max_epochs": 3})
    res = verify.verify(tmp_path / "m", n=3, seed=202)
    assert res["simulated"] <= 3 and sum(res["confusion"].values()) == res["usable"]


@needs_sim
def test_verify_failures_reruns_predicted_failures(tmp_path):
    """verify_failures() simulates only the predicted failures and returns the ones the simulator confirms."""
    csv = sdata.generate(30, 201, tmp_path / "gen.csv")
    train.train(csv, tmp_path / "m", seed=0, overrides={"max_epochs": 3})
    cands = scenario.sample_many(5, seed=203)
    out = verify.verify_failures(tmp_path / "m", cands)
    assert all(not row["passed"] and sc in cands for sc, row in out)


def test_constant_input_is_not_blown_up_and_extrapolation_is_flagged(encoder):
    """handback_delay_s is fixed at 0.2 s by the sampler, so its spread is floating-point noise (~1e-17): it must
    be treated as constant (std 1), keep LEGACY_UPS (3.0 s) finite, and be flagged as outside the training range."""
    assert encoder.std["handback_delay_s"] == 1.0
    x = encoder.transform([scenario.LEGACY_UPS, scenario.GRID_FRIENDLY])
    assert np.isfinite(x).all() and np.abs(x).max() < 1e3
    flags = encoder.outside_training([scenario.LEGACY_UPS, scenario.GRID_FRIENDLY])
    assert "handback_delay_s" in flags[0] and "handback_delay_s" not in flags[1]


def test_recovery_margin_never_exceeds_the_deadline(encoder):
    """recovery_margin_s = deadline - recovery time, so every prediction is capped at the 2.0 s deadline."""
    from sim import constants as C
    pr = Ensemble.create(encoder, seed=0).predict(encoder.transform(scenario.sample_many(2_000, seed=18)))
    assert (pr["recovery_margin_s_mean"] <= C.RECOVERY_DEADLINE_S + 1e-12).all()
