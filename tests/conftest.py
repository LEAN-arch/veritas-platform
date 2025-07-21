# tests/conftest.py

import pytest
import pandas as pd
import sys
import os

# This setup allows pytest to find the 'veritas' package in the 'src' directory
# without having to install it. It's a standard practice for 'src' layouts.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from veritas.repository import MockDataRepository

@pytest.fixture(scope="session")
def mock_repo() -> MockDataRepository:
    """
    A session-scoped fixture that initializes the MockDataRepository once
    and makes it available to all tests in the session.

    'scope="session"' is highly efficient as it prevents re-creating the
    data repository for every single test function. It's created once
    at the beginning of the test run and destroyed at the end.
    A fixed seed is used to ensure the mock data is identical for every
    test run, leading to predictable and non-flaky tests.
    """
    return MockDataRepository(seed=42)

@pytest.fixture
def hplc_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """
    Provides a fresh copy of the HPLC data for a single test.

    This fixture depends on the `mock_repo` fixture. Pytest automatically
    injects the `mock_repo` instance. It calls the `get_data` method
    to retrieve the HPLC dataset. Because it is function-scoped (the default),
    each test function gets a pristine, unmodified copy of the data.
    """
    return mock_repo.get_data('hplc')

@pytest.fixture
def stability_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """
    Provides a fresh copy of the stability data for a single test.

    Similar to `hplc_data`, this provides a predictable dataset for
    testing stability-related analytics functions.
    """
    return mock_repo.get_data('stability')

@pytest.fixture
def deviations_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """
    Provides a fresh copy of the deviations data for a single test.
    """
    return mock_repo.get_data('deviations')

@pytest.fixture
def audit_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """
    Provides a fresh copy of the audit log data for a single test.
    """
    return mock_repo.get_data('audit')
