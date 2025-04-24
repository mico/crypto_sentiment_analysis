from typing import Dict, List

import pandas as pd
import pytest
from pytest_bdd import given, scenarios, then, when
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from app import prepare_data, POSITIVE_THRESHOLD, NEGATIVE_THRESHOLD
from database import Base, SentimentData
from datetime import datetime
# Register scenarios from the data preparation feature file
scenarios('../data_preparation.feature')


@pytest.fixture
def test_engine() -> Engine:
    """Create an in-memory SQLite database for testing."""
    return create_engine('sqlite:///:memory:')


@pytest.fixture
def sample_data() -> List[Dict]:
    """Create sample sentiment data for testing."""
    return [
        {
            "id": "1",
            "domain": "reddit.com",
            "title": "Bitcoin is amazing!",
            "coins": "BTC",
            "published_at": "2023-05-01T12:00:00Z",
            "url": "https://reddit.com/r/Bitcoin/123",
            "sentiment": 0.8  # Positive sentiment
        },
        {
            "id": "2",
            "domain": "reddit.com",
            "title": "Ethereum development update",
            "coins": "ETH",
            "published_at": "2023-05-01T13:00:00Z",
            "url": "https://reddit.com/r/ethereum/456",
            "sentiment": 0.1  # Neutral sentiment
        },
        {
            "id": "3",
            "domain": "cryptopanic.com",
            "title": "Market crash imminent?",
            "coins": "BTC,ETH",
            "published_at": "2023-05-01T14:00:00Z",
            "url": "https://cryptopanic.com/news/789",
            "sentiment": -0.7  # Negative sentiment
        }
    ]


@given("the database contains sentiment data", target_fixture="mock_db_data")
def given_database_with_data(test_engine: Engine, sample_data: List[Dict]) -> pd.DataFrame:
    """Set up a mock database with sample data."""
    Base.metadata.create_all(test_engine)
    session = Session(test_engine)

    try:
        # Insert data using the SentimentData model
        for item in sample_data:
            # Convert sentiment to string to match the database schema
            item_copy = item.copy()
            item_copy["sentiment"] = str(item_copy["sentiment"])

            if isinstance(item_copy["published_at"], str):
                item_copy["published_at"] = datetime.fromisoformat(
                    item_copy["published_at"].replace("Z", "+00:00")
                )

            sentiment_data = SentimentData(**item_copy)
            session.add(sentiment_data)

        session.commit()

        # Read back the data to verify it was inserted correctly
        df = pd.read_sql_query("SELECT * FROM sentiment_data", test_engine)
        return df
    finally:
        session.close()


@when("I prepare the data", target_fixture="prepared_data")
def when_prepare_data(mock_db_data: pd.DataFrame, test_engine: Engine) -> pd.DataFrame:
    """Call the prepare_data function with a mock database."""
    result = prepare_data(test_engine)
    return result


@then("the result should be a DataFrame")
def then_result_is_dataframe(prepared_data: pd.DataFrame) -> None:
    """Check if the result is a pandas DataFrame."""
    assert isinstance(prepared_data, pd.DataFrame)
    assert not prepared_data.empty


@then("the DataFrame should have a 'published_at' column with datetime values")
def then_has_datetime_column(prepared_data: pd.DataFrame) -> None:
    """Check if the published_at column has datetime values."""
    assert 'published_at' in prepared_data.columns
    assert pd.api.types.is_datetime64_any_dtype(prepared_data['published_at'])


@then("the DataFrame should have a 'sentiment_category' column")
def then_has_sentiment_category_column(prepared_data: pd.DataFrame) -> None:
    """Check if the sentiment_category column exists."""
    assert 'sentiment_category' in prepared_data.columns


@then("the sentiment categories should be correctly assigned")
def then_sentiment_categories_correct(prepared_data: pd.DataFrame) -> None:
    """Check if sentiment categories are correctly assigned based on thresholds."""
    # Sample specific records by their ID and check their sentiment category
    record1 = prepared_data[prepared_data['id'] == '1'].iloc[0]
    record2 = prepared_data[prepared_data['id'] == '2'].iloc[0]
    record3 = prepared_data[prepared_data['id'] == '3'].iloc[0]

    # Verify sentiment categories
    assert record1['sentiment_category'] == "Positive"  # Sentiment 0.8 > POSITIVE_THRESHOLD
    assert record2['sentiment_category'] == "Neutral"   # Sentiment 0.1 between thresholds
    assert record3['sentiment_category'] == "Negative"  # Sentiment -0.7 < NEGATIVE_THRESHOLD

    # Additional verification for all records
    positive_records = prepared_data[prepared_data['sentiment'] > POSITIVE_THRESHOLD]
    neutral_records = prepared_data[(prepared_data['sentiment'] >= NEGATIVE_THRESHOLD) &
                                    (prepared_data['sentiment'] <= POSITIVE_THRESHOLD)]
    negative_records = prepared_data[prepared_data['sentiment'] < NEGATIVE_THRESHOLD]

    assert all(positive_records['sentiment_category'] == "Positive")
    assert all(neutral_records['sentiment_category'] == "Neutral")
    assert all(negative_records['sentiment_category'] == "Negative")
