"""ship: one prompt, one safely travelled commit.

The SHIP law (law.py, vendored from ship.c) decides how far a working-tree
change may travel: nowhere, into the index, into local history, or out to the
remote.  The body (measure.py) measures the eight observations the law reads;
the eyes (eyes.py, a local model) write the summary and nothing else; the
pipeline (pipeline.py) runs exactly as far as the ruling says.
"""
from .law import ship, NONE, STAGE, COMMIT, PUSH
from .pipeline import run, rule, actuate

__version__ = "0.1.0"
__all__ = ["ship", "run", "rule", "actuate", "NONE", "STAGE", "COMMIT", "PUSH", "__version__"]
