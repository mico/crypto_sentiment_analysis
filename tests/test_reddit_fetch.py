import os
import pytest
import vcr
from datetime import datetime
import pandas as pd
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv
from pytest_bdd import scenarios, given, when, then, parsers
from pytest_bdd.parser import Feature, Scenario

# Load the .env.testing file
load_dotenv('.env.testing')

# Import the functions to test
from reddit_fetch import (
    fetch_reddit_data, 
    determine_sentiment, 
    extract_mentioned_coins, 
    get_coin_keywords
)

# Configure VCR
# This will create cassettes (recorded API responses) in the fixtures/vcr_cassettes directory
my_vcr = vcr.VCR(
    cassette_library_dir='fixtures/vcr_cassettes',
    record_mode='once',
    match_on=['uri', 'method'],
)

# Register all scenarios from feature files
scenarios('features/coin_extraction.feature')
scenarios('features/sentiment_analysis.feature')
scenarios('features/reddit_data_fetching.feature')
scenarios('features/submission_analysis.feature')

# Hook to add VCR for scenarios with @vcr tag
@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    """Apply VCR cassette for scenarios tagged with @vcr."""
    if pyfuncitem.funcargs.get('request') and hasattr(pyfuncitem.funcargs['request'], 'getfixturevalue'):
        try:
            if 'fetch_subreddit_data' in pyfuncitem._fixtureinfo.argnames:
                subreddit = pyfuncitem.funcargs.get('subreddit') or pyfuncitem._fixtureinfo.funcargs.get('subreddit')
                if subreddit:
                    cassette_name = f'test_fetch_reddit_{subreddit.lower()}_data'
                    with my_vcr.use_cassette(f'{cassette_name}.yaml'):
                        yield
                        return
        except (AttributeError, KeyError):
            pass
    
    yield  # Default behavior for other functions

# Fixtures ----------------------------------------------

@pytest.fixture
def reddit_client():
    """Create a real Reddit client for testing."""
    # For tests, you can use environment variables or test-specific credentials
    client_id = os.environ.get("TEST_REDDIT_CLIENT_ID") or "your_test_client_id"
    client_secret = os.environ.get("TEST_REDDIT_CLIENT_SECRET") or "your_test_client_secret"
    user_agent = os.environ.get("TEST_REDDIT_USER_AGENT") or "python:crypto-sentiment-test:v1.0"
    
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

@pytest.fixture
def sentiment_analyzer():
    """Create a real VADER sentiment analyzer."""
    return SentimentIntensityAnalyzer()

@pytest.fixture
def test_coin_keywords():
    """Provide a smaller set of coin keywords for testing."""
    return {
        'BTC': ['BTC', 'BITCOIN', 'BTCUSD'],
        'ETH': ['ETH', 'ETHEREUM', 'ETHUSD'],
        'ADA': ['ADA', 'CARDANO', 'HOSKINSON'],
        'SOL': ['SOL', 'SOLANA']
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

@given("a Reddit client", target_fixture="client")
def given_reddit_client(reddit_client):
    """Return Reddit client for use in steps."""
    return reddit_client

@given("a sentiment analyzer", target_fixture="analyzer")
def given_sentiment_analyzer(sentiment_analyzer):
    """Return sentiment analyzer for use in steps."""
    return sentiment_analyzer

# Feature: Coin Extraction Steps -----------------------

@when(parsers.parse('I analyze the title "{title}" and content "{content}"'), target_fixture="extraction_data")
def analyze_text(title, content, coin_keywords):
    """Analyze text for coin mentions and store input for later assertions."""
    return {
        "title": title, 
        "content": content, 
        "coin_keywords": coin_keywords,
        "result": extract_mentioned_coins(title, content, coin_keywords)
    }

@then(parsers.parse('the extracted coins should include "{coin}"'))
def extracted_coins_include(extraction_data, coin):
    """Check if extracted coins include the expected coin."""
    assert coin in extraction_data["result"]

@then(parsers.parse('the extracted coins should not include "{coin}"'))
def extracted_coins_not_include(extraction_data, coin):
    """Check if extracted coins don't include the specified coin."""
    coins = extraction_data["result"]
    assert coin not in coins.split(',') if coins else True

@then("there should be no extracted coins")
def no_extracted_coins(extraction_data):
    """Check if no coins were extracted."""
    assert extraction_data["result"] == ''

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

# Feature: Reddit Data Fetching Steps -----------------

@when(parsers.parse('I fetch data from the "{subreddit}" subreddit'), target_fixture="fetch_results")
def fetch_subreddit_data(subreddit, client, analyzer, coin_keywords):
    """Fetch data from a specific subreddit."""
    # For Bitcoin, use only BTC keywords to ensure matches
    if subreddit == "Bitcoin":
        btc_keywords = {'BTC': coin_keywords['BTC']}
        with my_vcr.use_cassette(f'test_fetch_reddit_{subreddit.lower()}_data.yaml'):
            result = fetch_reddit_data(client, subreddit, analyzer, btc_keywords)
    else:
        with my_vcr.use_cassette(f'test_fetch_reddit_{subreddit.lower()}_data.yaml'):
            result = fetch_reddit_data(client, subreddit, analyzer, coin_keywords)
    
    return {
        "result": result, 
        "subreddit": subreddit
    }

@then("I should get a list of post data")
def check_post_data_list(fetch_results):
    """Check if the result is a list and contains data."""
    result = fetch_results["result"]
    assert isinstance(result, list)
    assert len(result) > 0

@then(parsers.parse('each post should mention "{coin}"'))
def each_post_mentions_coin(fetch_results, coin):
    """Check if each post mentions the specified coin."""
    result = fetch_results["result"]
    for post_data in result:
        assert coin in post_data['coins']

@then("each post should contain the required fields")
def check_post_fields(fetch_results):
    """Check if each post contains all the required fields."""
    result = fetch_results["result"]
    for post_data in result:
        assert 'id' in post_data and post_data['id'].startswith('RD_')
        assert 'domain' in post_data and post_data['domain'] == 'reddit.com'
        assert 'title' in post_data and isinstance(post_data['title'], str)
        assert 'published_at' in post_data and isinstance(post_data['published_at'], datetime)
        assert 'url' in post_data and post_data['url'].startswith('https://www.reddit.com/')
        assert 'sentiment' in post_data

@then("each post should have a sentiment classification")
def check_sentiment_field(fetch_results):
    """Check if each post has a sentiment classification."""
    result = fetch_results["result"]
    for post_data in result:
        assert post_data['sentiment'] in ['Positive', 'Neutral', 'Negative']

@then("the results should include mentions of at least one test coin")
def check_mentions_test_coins(fetch_results, coin_keywords):
    """Check if the results include mentions of at least one test coin."""
    result = fetch_results["result"]
    
    coins_mentioned = set()
    for post_data in result:
        if post_data['coins']:
            coins = post_data['coins'].split(',')
            coins_mentioned.update(coins)
    
    assert len(coins_mentioned.intersection(set(coin_keywords.keys()))) > 0 

# Feature: Submission Analysis Steps -----------------

@given("I have loaded test submissions from fixtures", target_fixture="submissions_dir")
def given_test_submissions(test_submissions_dir):
    """Return the path to test submissions directory"""
    return test_submissions_dir

@when(parsers.parse('I analyze the submission with ID "{submission_id}"'), target_fixture="analysis_result")
def analyze_test_submission(submission_id, submissions_dir, analyzer, coin_keywords):
    """Analyze a test submission by ID and return the result"""
    from reddit_fetch import load_test_submission, process_reddit_submission
    
    # Load the test submission
    submission = load_test_submission(submission_id, submissions_dir)
    
    # Process the submission
    result = process_reddit_submission(submission, analyzer, coin_keywords)
    
    return result

@then(parsers.parse('the sentiment should be classified as "{expected_sentiment}"'))
def check_sentiment_classification(analysis_result, expected_sentiment):
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