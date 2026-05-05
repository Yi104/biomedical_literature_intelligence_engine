import random, os, numpy as np, torch

# Shared extraction utilities.

def set_seed(seed):
    # Keep training/inference behavior reproducible across runs.
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
