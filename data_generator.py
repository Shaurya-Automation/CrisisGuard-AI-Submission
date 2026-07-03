# Filename: data_generator.py
"""
CrisisGuard-AI :: Data Generator

Simulates a live social-media-style feed so the whole pipeline can be
demoed and tested with zero budget and no external API keys. Mixes
clearly safe posts with warning- and critical-level posts across every
crisis category the AnalystAgent understands.
"""

import random

SAFE_POSTS = [
    "Just passed my exam, feeling great today!",
    "Beautiful sunset at the beach this evening.",
    "Had a great cup of coffee this morning.",
    "Our team won the local cricket match yesterday.",
    "New restaurant downtown has amazing food.",
    "Finished reading a really good book this week.",
]

WARNING_POSTS = [
    "Feeling really overwhelmed with everything lately.",
    "Small kitchen fire, put out quickly, everyone is fine.",
    "Noticed some suspicious login attempts on my account.",
    "Loud argument outside, hope it doesn't escalate.",
    "I've been feeling so alone the past few weeks.",
    "Traffic accident on the highway, minor injuries reported.",
]

CRITICAL_POSTS = [
    "Fire spreading fast in the apartment building, need help now!",
    "Our company server has been hacked, customer data may be leaked.",
    "I don't want to be here anymore, I want to end it all.",
    "Explosion reported near the market, people are running.",
    "Active shooting reported downtown, please stay away from the area.",
    "Ransomware locked all hospital systems, patients at risk.",
    "Building collapsed after the earthquake, people trapped inside.",
    "He said he wants to kill himself, I don't know what to do.",
]

_ALL_POOLS = (
    [(t, "safe") for t in SAFE_POSTS]
    + [(t, "warning") for t in WARNING_POSTS]
    + [(t, "critical") for t in CRITICAL_POSTS]
)


def generate_simulated_posts(n: int = 10, seed: int | None = None) -> list[dict]:
    """
    Return a list of {"source": "simulated_social", "text": ...} dicts,
    randomly sampled across safe/warning/critical pools so a demo run
    always produces a realistic mix.
    """
    rng = random.Random(seed)
    chosen = [rng.choice(_ALL_POOLS) for _ in range(n)]
    return [{"source": "simulated_social", "text": text} for text, _label in chosen]


def generate_texts(n: int = 10, seed: int | None = None) -> list[str]:
    """Convenience helper: just the raw text strings."""
    return [p["text"] for p in generate_simulated_posts(n, seed=seed)]


if __name__ == "__main__":
    for post in generate_simulated_posts(8, seed=42):
        print(f"[{post['source']}] {post['text']}")
