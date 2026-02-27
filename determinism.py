# determinism.py

import random
import numpy as np
import torch


def set_deterministic(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)

    try:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except Exception:
        pass
