"""Common interface: every factor exposes a sampler with provenance metadata."""
from dataclasses import dataclass
import numpy as np


@dataclass
class FactorModel:
    name: str
    units: str
    source_id: str  # row in sources.csv
    kind: str  # "observed" or "assumption"

    def sample(self, n: int, rng: np.random.Generator, **conditions):
        raise NotImplementedError
