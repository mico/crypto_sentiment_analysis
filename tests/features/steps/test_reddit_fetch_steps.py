import os

import pytest
import vcr
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import reddit_fetch
from database import SentimentData, get_session

# Register scenarios from feature files
scenarios('../reddit_fetch.feature')

# Constants
TEST_DB_PATH: str = "test_crypto_data.db"

# Setup VCR for recording/replaying API interactions
vcr_instance: vcr.VCR = vcr.VCR(
    cassette_library_dir="tests/fixtures/vcr_cassettes",
    record_mode=os.environ.get("VCR_RECORD_MODE", "new_episodes"),
    match_on=["uri", "method"],
    filter_headers=["Authorization", "User-Agent"],
    serializer="yaml",
    decode_compressed_response=True,
)


# Fixtures
@pytest.fixture
def setup_config() -> reddit_fetch.Config:
    return reddit_fetch.Config(subreddits=["Bitcoin"],
                               coin_keywords={
                                 "BTC": ["BITCOIN", "BTC"],
                                 "ETH": ["ETHEREUM", "ETH"]
                               },
                               general_terms=["crypto", "cryptocurrency"],
                               db_path=TEST_DB_PATH,
                               posts_limit=5)


@given("a Configuration file for test", target_fixture="config")
def configuration_file(setup_config: reddit_fetch.Config) -> reddit_fetch.Config:
    return setup_config


@given("the test database is set up", target_fixture="test_engine")
def test_database_setup(setup_test_db: Engine) -> Engine:
    """Set up the test database."""
    return setup_test_db


@when(parsers.parse('I run the complete data fetch workflow'))
def run_complete_workflow(config: reddit_fetch.Config) -> None:
    """Run the complete data fetch workflow."""
    with vcr_instance.use_cassette("reddit_complete_workflow.yaml"):
        # Use a test configuration with limited scope

        # Fetch posts
        reddit_fetch.main(config)

        return


@then("I should be able to retrieve the posts from the database")
def check_posts_retrievable(test_engine: Engine, config: reddit_fetch.Config) -> None:
    """Check that posts can be retrieved from the database."""
    session: Session = get_session(test_engine)
    try:
        posts_count = session.query(SentimentData).count()
        assert posts_count > 0

        # Check a post
        post = session.query(SentimentData).first()
        assert post is not None
        assert post.id.startswith("RD_")
    finally:
        session.close()


# @then("each submission should have the correct structure")
# def check_submission_structure(posts: List[reddit_fetch.ProcessedSubmission]) -> None:
#     """Check that each submission has the correct structure."""
#     for post in posts:
#         assert isinstance(post, reddit_fetch.ProcessedSubmission)
#         assert post.id.startswith("RD_")
#         assert post.domain == "reddit.com"
#         assert isinstance(post.title, str)
#         assert isinstance(post.coins, list)
#         assert isinstance(post.published_at, datetime)
#         assert isinstance(post.url, str)
