"""
Unit tests for Day 2 synthetic supply chain dataset.
Ensures data integrity, schema compliance, and business logic constraints pass during pytest runs.
"""

import sys
from pathlib import Path
import pytest

# Add synthetic data directory to sys.path
data_dir = Path(__file__).resolve().parent.parent / "data" / "synthetic"
if str(data_dir) not in sys.path:
    sys.path.insert(0, str(data_dir))

from validate_supply_chain_data import validate_dataset


def test_synthetic_supply_chain_dataset_valid():
    """Verify that the synthetic dataset satisfies all schema and business logic requirements."""
    assert validate_dataset() is True
