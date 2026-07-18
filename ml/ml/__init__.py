"""SentinelleRx machine-learning package."""
import sys
from pathlib import Path

# Reuse the backend models + settings so ML and API share one schema definition.
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
