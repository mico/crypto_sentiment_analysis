import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Import the functions to test
from reddit_fetch import determine_sentiment

# Register scenarios from the sentiment analysis feature file
scenarios('features/sentiment_analysis.feature')

# Feature: Sentiment Analysis Steps -------------------

@when(parsers.parse("I have a sentiment score of {score:f}"), target_fixture="sentiment_context")
def create_sentiment_score(score):
    """Store sentiment score for later assertions."""
    return {
        "score": score,
        "sentiment": determine_sentiment(score)
    }

@then(parsers.parse('the sentiment should be classified as "{expected_sentiment}"'))
def check_sentiment_classification(sentiment_context, expected_sentiment):
    """Check if the sentiment is classified correctly."""
    assert sentiment_context["sentiment"] == expected_sentiment 