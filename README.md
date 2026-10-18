# GR1D
GR1D

**Scope (known limitation).** The simulator, and everything built on it (training data, surrogate, pipeline reports), is only trusted for grid dips whose **retained voltage is 0.70-0.90 pu** (`sim.constants.VALID_DIP_DEPTH_PU`), which covers about 69% of sags (Eaton/EPRI; `IN_SCOPE_SAG_SHARE`). Deeper sags hit an unresolved voltage-collapse / invalid-root problem in the voltage solution (see `validation/CROSSCHECK.md`), so they are out of scope for now: sampling stays inside the band by default (`sim.scenario.sample(..., in_scope_only=True)`), results are conditional on an in-band dip, and deeper sags are unassessed, neither pass nor fail.
