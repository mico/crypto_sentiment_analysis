import os
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Import the functions to test
from reddit_fetch import process_reddit_submission, load_config
from tests.utils import load_test_submission

# Register scenarios from the submission analysis feature file
scenarios('features/submission_analysis.feature')

@pytest.fixture
def test_config():
    """Load a test configuration or use the main one."""
    # You could create a test-specific config or use the main one
    return load_config('config.yaml')

@pytest.fixture
def sentiment_analyzer():
    """Create a real VADER sentiment analyzer."""
    return SentimentIntensityAnalyzer()

@pytest.fixture
def test_coin_keywords(test_config):
    """Provide a smaller set of coin keywords for testing."""
    # Use a subset of the main config for faster testing
    all_keywords = test_config['coin_keywords']
    return {
        'BTC': all_keywords['BTC'],
        'ETH': all_keywords['ETH'],
        'ADA': all_keywords['ADA'],
        'SOL': all_keywords['SOL']
    }

@pytest.fixture
def test_submissions_dir():
    """Path to test submission fixtures directory"""
    return os.path.join(os.path.dirname(__file__), 'fixtures', 'submissions')

# Common Steps -----------------------------------------

@given("a set of cryptocurrency keywords", target_fixture="coin_keywords")
def given_cryptocurrency_keywords(test_coin_keywords):
    """Return coin keywords for use in steps."""
    return test_coin_keywords

@given("a sentiment analyzer", target_fixture="analyzer")
def given_sentiment_analyzer(sentiment_analyzer):
    """Return sentiment analyzer for use in steps."""
    return sentiment_analyzer

@given("I have loaded test submissions from fixtures", target_fixture="submissions_dir")
def given_test_submissions(test_submissions_dir):
    """Return the path to test submissions directory"""
    return test_submissions_dir

# Feature: Submission Analysis Steps -----------------

@when(parsers.parse('I analyze the submission with ID "{submission_id}"'), target_fixture="analysis_result")
def analyze_test_submission(submission_id, submissions_dir, analyzer, coin_keywords):
    """Analyze a test submission by ID and return the result"""
    # Load the test submission
    submission = load_test_submission(submission_id, submissions_dir)
    
    # Process the submission
    result = process_reddit_submission(submission, analyzer, coin_keywords)
    
    return result

@then(parsers.parse('the sentiment should be classified as "{expected_sentiment}"'))
def check_submission_sentiment(analysis_result, expected_sentiment):
    """Check if the sentiment classification matches the expected value"""
    assert analysis_result['sentiment'] == expected_sentiment

@then(parsers.parse('the extracted coins should include "{expected_coins}"'))
def check_extracted_coins(analysis_result, expected_coins):
    """Check if the extracted coins include the expected values"""
    coins = analysis_result['coins'].split(',') if analysis_result['coins'] else []
    expected = expected_coins.split(',') if expected_coins else []
    
    for coin in expected:
        assert coin in coins, f"Expected coin {coin} not found in extracted coins: {coins}"

@then(parsers.parse('the submission title should contain "{title_keyword}"'))
def check_submission_title(analysis_result, title_keyword):
    """Check if the submission title contains the expected keyword"""
    assert title_keyword.lower() in analysis_result['title'].lower(), \
        f"Expected keyword '{title_keyword}' not found in title: {analysis_result['title']}"

@then(parsers.parse('the submission should be from the "{subreddit}" subreddit'))
def check_submission_subreddit(analysis_result, subreddit):
    """Check if the submission is from the expected subreddit"""
    # Extract subreddit from URL
    # URL format is https://www.reddit.com/r/subreddit/...
    url_parts = analysis_result['url'].split('/')
    actual_subreddit = url_parts[4] if len(url_parts) > 4 else ""
    
    assert actual_subreddit.lower() == subreddit.lower(), \
        f"Expected subreddit '{subreddit}' but got '{actual_subreddit}'" 