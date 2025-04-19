from pytest_bdd import parsers, scenarios, then, when

# Import the functions to test
from reddit_fetch import determine_sentiment

from pydantic import BaseModel

# Register scenarios from the sentiment analysis feature file
scenarios('features/sentiment_analysis.feature')


class SentimentContext(BaseModel):
    score: float
    sentiment: str


@when(parsers.parse("I have a sentiment score of {score:f}"), target_fixture="sentiment_context")
def create_sentiment_score(score: float) -> SentimentContext:
    """Store sentiment score for later assertions."""
    return SentimentContext(score=score, sentiment=determine_sentiment(score))


@then(parsers.parse('the sentiment should be classified as "{expected_sentiment}"'))
def check_sentiment_classification(sentiment_context: SentimentContext, expected_sentiment: str) -> None:
    """Check if the sentiment is classified correctly."""
    assert sentiment_context.sentiment == expected_sentiment
