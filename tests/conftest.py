import os
import sys
import pytest
from typing import Any, Optional, Generator
from pathlib import Path

from sqlalchemy.engine import Engine

from database import get_engine, init_db
from tests.utils import load_test_env

# Load test environment variables
load_test_env()

# Constants
TEST_DB_PATH: str = "test_crypto_data.db"


# Add fixtures available to all tests
@pytest.fixture(scope="function")
def setup_test_db() -> Generator[Engine, None, None]:
    """Create a test database and initialize tables."""
    # Create engine with test db
    engine: Engine = get_engine(TEST_DB_PATH)
    # Initialize database schema
    init_db(engine)

    yield engine

    # Cleanup after test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


# Create paths for VCR cassettes
@pytest.fixture(scope="session", autouse=True)
def ensure_cassette_dir() -> None:
    """Ensure the cassette directory exists."""
    cassette_dir = Path("tests/fixtures/vcr_cassettes")
    cassette_dir.mkdir(parents=True, exist_ok=True)


# Configure pytest-bdd
def pytest_bdd_apply_tag(tag: str, function: Any) -> Optional[bool]:
    """Apply pytest-bdd tags to tests."""
    if tag == "integration":
        # Mark as integration test
        marker = pytest.mark.integration
        marker(function)
        return True
    elif tag == "vcr":
        # Mark as using VCR
        marker = pytest.mark.vcr
        marker(function)
        return True
    # Let pytest-bdd handle other tags
    return None
