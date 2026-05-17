import os
import random
import numpy as np
import torch


def set_deterministic(seed: int = 42, warn_only: bool = False):
    """
    Fully enforce reproducibility across Python, NumPy, and PyTorch.

    Args:
        seed (int): Random seed
        warn_only (bool): If True, allows nondeterministic ops with warnings
    """

    # ----------------------------
    # 🌱 Python + NumPy
    # ----------------------------
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    # ----------------------------
    # 🔥 PyTorch RNG
    # ----------------------------
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # ----------------------------
    # ⚙️ Deterministic behavior
    # ----------------------------
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    # Enforce deterministic algorithms
    torch.use_deterministic_algorithms(True, warn_only=warn_only)

    # ----------------------------
    # ⚡ CUDA / matmul determinism
    # ----------------------------
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

    # ----------------------------
    # 🧵 Threading control (optional)
    # ----------------------------
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    return seed