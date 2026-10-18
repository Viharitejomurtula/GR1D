"""Surrogate hyperparameters and training settings.

What this file is
    The single CONFIG dict read by every other surrogate module. Every value is a DESIGN CHOICE, not
    a measured or sourced quantity: change them here, not in code. Values marked "(spec)" were given
    in the task specification; values marked "(my choice)" were not specified there.

Inputs / outputs: none (constants only).
"""

CONFIG = {
    # --- ensemble (design choice) ---
    "n_members": 5,                       # K (spec)
    "hidden_sizes": [128, 128, 128],      # three hidden Linear layers (spec)
    "dropout": 0.1,                       # after the first two hidden layers (spec)
    # --- optimisation (design choice) ---
    "lr": 1e-3,                           # AdamW learning rate (spec)
    "weight_decay": 1e-2,                 # AdamW default weight decay (my choice: torch default)
    "batch_size": 256,                    # (spec)
    "patience": 20,                       # early-stopping epochs without validation improvement (spec)
    "max_epochs": 500,                    # (spec)
    "huber_delta": 1.0,                   # Huber transition, in standardized margin units (my choice: torch default)
    # --- loss weights (design choice; equal weights are my choice, spec gave none) ---
    "loss_weights": {
        "passed": 1.0,                    # BCE
        "recovery_margin_s": 1.0,         # Huber / censored hinge
        "min_power": 1.0,                 # MSE
        "peak_current_pu": 1.0,           # MSE
        "floor_violation_s": 1.0,         # MSE on log1p
        "failure_mode": 1.0,              # cross-entropy
    },
    # --- data split (design choice) ---
    "split": {"train": 0.70, "val": 0.15, "test": 0.15},   # stratified on passed (spec)
    "split_seed_offset": 0,               # split uses the train() seed plus this (my choice)
    "edge_band_s": 0.25,                  # edge subset: test rows with |recovery_margin_s| < this (spec)
    # --- inference and export (design choice) ---
    "predict_batch": 65_536,              # rows per forward pass in predict.py (my choice)
    "onnx_opset": 17,                     # (spec)
    "onnx_parity_atol": 1e-4,             # ONNX vs PyTorch tolerance (spec)
    "uncertainty_k": 2.0,                 # "within mean +/- k std" in metrics and verify (spec: 2)
    # --- uncertainty calibration and data checks (design choice, my choice) ---
    "calibrate_std": True,                # rescale each regression std on the validation split (train.calibrate)
    "min_class_rows": 3,                  # warn when a failure_mode has fewer rows than this in val or test
    "ood_margin_frac": 0.01,              # an input is "outside training" beyond its training range +/- this x range (my choice)
}
