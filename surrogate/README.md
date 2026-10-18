# Surrogate

Neural surrogate of the ride-through simulator. Models live in `surrogate/models/<name>/`; the active one is
chosen by `surrogate/registry.py`, and everything downstream (`ridethrough/pipeline/*`, `api/main.py`) gets
its model from there.

## Swapping the surrogate

The pipeline relies only on `surrogate.registry.SurrogateModel`:

- `classes: list[str]` failure-mode labels, including `"passed"`
- `input_fields: list[str]`
- `provenance: dict` (name, format, training data; copied into reports)
- `predict(frame_or_scenarios) -> DataFrame` with `p_pass_mean`, `p_pass_std`, `<t>_mean`/`<t>_std` for
  `recovery_margin_s`, `min_power`, `peak_current_pu`, `floor_violation_s`, `failure_mode`,
  `failure_mode_prob`, `outside_training` (`";"`-joined, `""` when none) and `prob:<class>` for every class
- `member_fail_probs(frame) -> (n_members, m)` array (a single model returns `(1, m)`)

Steps:

1. Put the model in `surrogate/models/<name>/`.
2. Add `surrogate/models/<name>/manifest.json`, for example `{"format": "torch-ensemble", "name": "<name>"}`.
   With no manifest, the format defaults to `torch-ensemble` (the format of v1: `encoder.json`, `config.json`,
   `member_<i>.pt`, optional `calibration.json`).
3. If the format is new, register a loader once (for example at the bottom of `surrogate/registry.py`):
   ```python
   def _load_mine(model_dir: Path, manifest: dict) -> SurrogateModel: ...
   register_loader("my-format/1", _load_mine)
   ```
4. Select it. The order is: explicit argument, then env var, then pointer file.
   - `echo <name> > surrogate/models/ACTIVE` (the default for everything)
   - or `GR1D_SURROGATE=<name or path>` for one shell
   - or `python -m ridethrough.pipeline.run --model <name or path> ...` for one run
5. Re-export the numpy JSON for the API and browser: `python -m surrogate.web`. This writes
   `surrogate/models/<active>/web.json` (the API serves it when present; `SURROGATE_JSON` overrides) and
   copies it to `frontend/public/data/surrogate.json` (the browser, and the Docker image, use that copy).
   `export_web` reads torch-ensemble weights, so a new architecture needs its own exporter to the same JSON
   format, or the API keeps serving the previous JSON. `GET /health` reports which model the API loaded.
6. Check the contract and the pipeline:
   `.venv/bin/python -m pytest -q tests/test_registry.py tests/test_pipeline.py -p no:cacheprovider`
   (add the new model to `test_v1_via_registry`, or copy that test), then run
   `.venv/bin/python -m ridethrough.pipeline.run --n 3000 --events 200 --perms 2 --out /tmp/p`. The report's
   `surrogate` entry and its "Surrogate model:" line name the model that was used.
