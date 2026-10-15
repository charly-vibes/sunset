"""Test path bootstrap for the substrate gate harness (sunset-7hs)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
