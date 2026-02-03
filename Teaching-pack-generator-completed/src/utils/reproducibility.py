from __future__ import annotations

import os
import random
from typing import Optional


def set_seed(seed: Optional[int]) -> None:
    if seed is None:
        return
    os.environ['PYTHONHASHSEED'] = str(seed)
    random.seed(seed)

    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass

    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass
