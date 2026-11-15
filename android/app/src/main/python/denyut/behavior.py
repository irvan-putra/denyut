"""Load the assistant's behavior configuration.

Everything the assistant does is driven by an ordinary JSON file that the
owner can read and edit. No hidden prompts or hardcoded personality.
"""

import json
import os

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "behavior.json")


def load_behavior(path=None):
    path = path or os.environ.get("ASSISTANT_BEHAVIOR") or DEFAULT_PATH
    with open(path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg["_path"] = os.path.abspath(path)
    return cfg
