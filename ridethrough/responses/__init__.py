"""ridethrough.responses: data-derived driver -> factor responses for the S matrix.

Package marker. Modules:
    battery_resistance: storage resistance vs temperature (Panasonic 18650PF and Sandia EIS) and
                        cell-to-cell spread (Sandia EIS replicates).

Reads:  data_bayesian-network/drivers_raw/ (downloaded datasets, read-only).
Writes: data_bayesian-network/network/responses/ (via each module's main()).
"""
