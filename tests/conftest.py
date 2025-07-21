# tests/conftest.py

import pytest
import pandas as pd

# The sys.path hack is no longer needed due to the pyproject.toml setup.
# Pytest can now find the 'veritas' package directly.
from veritas.repository import MockDataRepository

@pytest.fixture(scope="session")
def mock_repo() -> MockDataRepository:
    """
    A session-scoped fixture that initializes the MockDataRepository once
    and makes it available to all tests in the session.

    'scope="session"' is highly efficient as it prevents re-creating the
    data repository for every single test function. It's created once
    at the beginning of the test run and destroyed at the end.
    """
    # Using a fixed seed ensures that the mock data is identical for every
    # test run, leading to predictable and non-flaky tests.
    return MockDataRepository(seed=42)

@pytest.fixture
def hplc_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """
    Provides a fresh copy of the HPLC data for a test.

    This fixture depends on the `mock_repo` fixture. Pytest automatically
    injects the `mock_repo` instance. It calls the `get_data` method
    to retrieve the HPLC dataset.
    """
    return mock_repo.get_data('hplc')

@pytest.fixture
def stability_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """
    Provides a fresh copy of the stability data for a test.

    Similar to `hplc_data`, this provides a predictable dataset for
    testing stability-related analytics functions.
    """
    return mock_repo.get_data('stability')

@pytest.fixture
def deviations_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """

    Provides a fresh copy of the deviations data for a test.
    """
    return mock_repo.get_data('deviations')
