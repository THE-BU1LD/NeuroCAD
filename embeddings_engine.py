# embeddings_engine.py

import numpy as np
import hashlib
from typing import Dict, List


class EmbeddingEngine:

    def __init__(self, dim: int = 128):
        self.dim = dim
        self.known_domains = [
            "aircraft",
            "automotive",
            "sports",
            "packaging",
            "mechanical",
            "architecture",
            "consumer_product"
        ]

    # ----------------------------
    # Deterministic Text Embedding
    # ----------------------------

    def text_to_seed(self, text: str) -> int:
        return int(hashlib.md5(text.encode()).hexdigest(), 16) % (10**8)

    def embed_text(self, text: str) -> np.ndarray:
        seed = self.text_to_seed(text)
        rng = np.random.default_rng(seed)
        return rng.normal(0, 1, self.dim)

    # ----------------------------
    # Domain Detection
    # ----------------------------

    def detect_domain(self, prompt: str) -> str:
        p = prompt.lower()
        for domain in self.known_domains:
            if domain in p:
                return domain

        if "plane" in p or "jet" in p or "wing" in p:
            return "aircraft"
        if "football" in p:
            return "sports"
        if "package" in p:
            return "packaging"

        return "consumer_product"

    # ----------------------------
    # Feature Extraction
    # ----------------------------

    def extract_numeric_features(self, prompt: str) -> Dict[str, float]:
        features = {}
        tokens = prompt.split()

        for i, t in enumerate(tokens):
            try:
                val = float(t)
                features[f"number_{i}"] = val
            except:
                continue

        return features

    # ----------------------------
    # Full Encoding
    # ----------------------------

    def encode_prompt(self, prompt: str) -> Dict:
        embedding = self.embed_text(prompt)
        domain = self.detect_domain(prompt)
        numbers = self.extract_numeric_features(prompt)

        return {
            "embedding": embedding,
            "domain": domain,
            "numerics": numbers
        }
