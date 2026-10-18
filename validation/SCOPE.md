# Validation scope and acceptance criteria (fixed 2026-10-18, before the work in steps 2-5 below)

## What the simulator claims to predict
For a single voltage-sag event (retained voltage 0.45-0.95 pu at the facility, 20 ms-2 s, up to 2 reclose dips, balanced or 1-2 of 3 phases faulted) on a
facility with ORv3-class PSU/BBU racks and VFD cooling, behind a transformer chain of 10-25% total %Z at X/R 8-12, with battery hall 15-35 C:
(a) pass/fail verdict and failure mode, (b) peak grid current, (c) fraction of load lost/sustained, (d) recovery time.

## Explicitly out of scope (not claimed)
Battery hall below 15 C; BBU discharge rates the cell datasheet does not cover; delta/ungrounded or otherwise phase-coupled supply paths;
retained voltage below the model's voltage-collapse boundary (runs are rejected as invalid, not predicted); harmonics and sub-cycle behaviour;
anything beyond the sampled input ranges in sim/scenario.py.

## Pass criteria (each must hold to say "validated" for that quantity)
| quantity | reference | criterion |
|---|---|---|
| network voltage at the PSUs | exact complex solve + DPsim | within 0.01 pu where a solution exists; invalid where none (MET, 1e-9) |
| PSU hold-up use in a sag | circuit-level model with SOURCED parameters | within 10% of energy used (BLOCKED: input-current limit unsourced) |
| battery usable energy vs temperature, 15-35 C | cell models (>=2 sets with a real temperature response) | within 10% (MET, ~7%) |
| battery usable energy at BBU rate | cell datasheet or power-cell model | within 10% (BLOCKED: no data) |
| peak grid current, held-out real events | measured | within 10% on at least 5 events, none used for fitting (2 events, both used for tuning) |
| sustained load loss, held-out real events | measured | within 10 percentage points on at least 5 events (NOT MET: 0.844 case +5.5 pt on 1 event; A is a fit) |
| recovery time, 70-sag benchmark | published benchmark | median within 25%, worst within 2x (median MET, worst 2.7x NOT MET) |
| verdict agreement with an independent composite of the engines | ngspice + DPsim + PyBaMM on 50+ scenarios | >= 95% (NOT RUN) |
Any "BLOCKED" or "NOT MET" row means that quantity is described as "cross-checked, with known gaps", never "validated".
No independent human review is available; this document is the substitute for pre-registration, so the thresholds are not to be changed after results are seen.
