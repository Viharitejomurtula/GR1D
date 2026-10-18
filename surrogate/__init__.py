"""Neural surrogate of the ride-through simulator: a deep ensemble of multi-output MLPs that maps a
sim.scenario.Scenario to the sim.grader.Grade outputs, with ensemble spread as uncertainty.

Modules: config (design choices), data (generate and load simulator runs), features (input encoding),
model (MemberNet, Ensemble), train, predict, export (ONNX), verify (check against the simulator).
Trained only on datasets produced by the actual simulator (sim.batch.run_batch).
"""
