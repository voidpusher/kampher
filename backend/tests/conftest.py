from __future__ import annotations

import os

# Deterministic test settings; no .env, no external services.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("KAMPHER_ENV", "dev")
os.environ.setdefault("KAMPHER_HN_ENABLED", "true")
