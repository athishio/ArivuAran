"""
tests/conftest.py - Pytest configuration and fixtures.
Ensures all tests execute against an isolated temporary SQLite database.
Production database (arivaran.db) is strictly protected from test pollution.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import db


@pytest.fixture(autouse=True)
def isolated_temp_db(tmp_path, monkeypatch):
    """Autouse fixture directing all db calls to a fresh temporary SQLite database."""
    test_db = tmp_path / "test_arivaran.db"
    monkeypatch.setenv("ARIVARAN_DB_PATH", str(test_db))
    db.init_db(str(test_db))
    yield
