# tests/step_defs/test_reddit_fetch_duplicates.py
from pydantic import HttpUrl
import pytest
from pytest_bdd import scenarios, given, when, then
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any
from sqlalchemy.engine import Engine
from datetime import datetime

# Assuming your project structure allows this import
# Adjust the import path based on your actual project structure
from reddit_fetch import store_submissions_in_database, ProcessedSubmission
from database import SentimentData, get_session

# Point scenarios to the feature file
scenarios('../reddit_fetch_duplicates.feature')


# Fixture to hold the state between steps
@pytest.fixture
def context() -> Dict[str, Any]:
    return {}


@given("the test database is set up", target_fixture="test_engine")
def test_database_setup(setup_test_db: Engine) -> Engine:
    """Set up the test database."""
    return setup_test_db


@given('the Reddit API returns posts with duplicate IDs')
def prepare_duplicate_post_data(context: Dict[str, Any]) -> None:
    """Prepares a list of post data containing duplicates."""
    duplicate_post_id: str = "RD_DUPLICATE_1"
    # Create ProcessedSubmission objects directly
    post_1 = ProcessedSubmission(
        id='RD_UNIQUE_1',
        domain='reddit.com',
        title='Unique Post 1',
        coins=['BTC'],
        published_at=datetime(2025, 4, 25, 10, 0, 0),
        url=HttpUrl('http://unique1.com'),
        sentiment=0.5
    )

    post_2_dup_a = ProcessedSubmission(
        id=duplicate_post_id,
        domain='reddit.com',
        title='Duplicate Post A',
        coins=['BTC'],
        published_at=datetime(2025, 4, 25, 11, 0, 0),
        url=HttpUrl('http://duplicate.com/a'),
        sentiment=0.6
    )

    post_3 = ProcessedSubmission(
        id='RD_UNIQUE_2',
        domain='reddit.com',
        title='Unique Post 2',
        coins=['ETH'],
        published_at=datetime(2025, 4, 25, 12, 0, 0),
        url=HttpUrl('http://unique2.com'),
        sentiment=0.7
    )

    # Using the same ID for the duplicate entry
    post_4_dup_b = ProcessedSubmission(
        id=duplicate_post_id,
        domain='reddit.com',
        title='Duplicate Post B',
        coins=['BTC'],
        published_at=datetime(2025, 4, 25, 11, 0, 0),
        url=HttpUrl('http://duplicate.com/b'),
        sentiment=0.6
    )

    post_5 = ProcessedSubmission(
        id='RD_UNIQUE_3',
        domain='reddit.com',
        title='Unique Post 3',
        coins=['BTC'],
        published_at=datetime(2025, 4, 25, 13, 0, 0),
        url=HttpUrl('http://unique3.com'),
        sentiment=0.8
    )

    posts_to_save: List[ProcessedSubmission] = [post_1, post_2_dup_a, post_3, post_4_dup_b, post_5]
    context['posts_to_save'] = posts_to_save
    context['duplicate_id'] = duplicate_post_id
    # Expected count is 3 unique + 1 duplicate = 4
    context['expected_unique_count'] = 4


@when('the Reddit posts are fetched and stored')
def attempt_to_store_posts(test_engine: Engine, context: Dict[str, Any]) -> None:
    """Attempts to save the prepared post data to the database."""
    posts_to_save = context.get('posts_to_save', [])
    context['exception'] = None  # To track unexpected errors

    try:
        # Call the assumed function to save the data
        store_submissions_in_database(posts_to_save, test_engine)
    except IntegrityError as e:
        # Let the test fail with IntegrityError, as this is the expected
        # behavior before the fix is implemented.
        raise e
    except Exception as e:
        # Capture other *unexpected* exceptions for debugging
        context['exception'] = e
        pytest.fail(f"An unexpected exception occurred during saving: {e}")


@then('the database contains only unique posts')
def check_database_unique_posts(test_engine: Engine, context: Dict[str, Any]) -> None:
    """Checks the database to ensure only unique posts were stored."""
    duplicate_id = context.get('duplicate_id')
    expected_unique_count = context.get('expected_unique_count')
    session: Session = get_session(test_engine)

    # Query the database for the total count
    total_posts_in_db: int = session.query(SentimentData).count()
    if total_posts_in_db != expected_unique_count:
        pytest.fail(
            f"Expected {expected_unique_count} unique posts in DB, but found {total_posts_in_db}"
        )

    # Query specifically for the duplicate ID to ensure only one entry exists
    if duplicate_id:
        # Break long line for query
        duplicate_posts_in_db: int = session.query(SentimentData)\
                                             .filter_by(id=duplicate_id)\
                                             .count()
        if duplicate_posts_in_db != 1:
            pytest.fail(
                f"Expected exactly 1 post with ID '{duplicate_id}' in DB, "
                f"but found {duplicate_posts_in_db}"
            )