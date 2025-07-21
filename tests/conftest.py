# tests/conftest.py

import pytest
import pandas as pd
from veritas.repository import MockDataRepository # Correct, direct import

@pytest.fixture(scope="session")
def mock_repo() -> MockDataRepository:
    """Session-scoped fixture to initialize the MockDataRepository once."""
    return MockDataRepository(seed=42)

@pytest.fixture
def hplc_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """Provides a fresh copy of the HPLC data for a test."""
    return mock_repo.get_data('hplc')

@pytest.fixture
def stability_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """Provides a fresh copy of the stability data for a test."""
    return mock_repo.get_data('stability')
