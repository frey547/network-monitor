from typing import Dict

import numpy as np


class SimulatedCollector:
    def collect(self) -> Dict[str, float]:
        return {
            "cpu": float(np.random.normal(30, 5)),
            "memory": float(np.random.normal(60, 10)),
        }
