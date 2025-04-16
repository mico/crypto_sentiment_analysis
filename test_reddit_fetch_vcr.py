import os
import pytest
import vcr
from datetime import datetime
import pandas as pd
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

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
    # filter_headers=['authorization', 'user-agent'],  # Don't record sensitive headers
    # filter_query_parameters=['auth_token', 'key', 'client_id', 'client_secret'],  # Don't record API keys
)

# Fixture for Reddit API client
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

# Fixture for VADER sentiment analyzer
@pytest.fixture
def sentiment_analyzer():
    """Create a real VADER sentiment analyzer."""
    return SentimentIntensityAnalyzer()

# Fixture for test coin keywords (smaller set for faster tests)
@pytest.fixture
def test_coin_keywords():
    """Provide a smaller set of coin keywords for testing."""
    return {
        'BTC': ['BTC', 'BITCOIN', 'BTCUSD'],
        'ETH': ['ETH', 'ETHEREUM', 'ETHUSD']
    }

# Test extract_mentioned_coins function
def test_extract_mentioned_coins(test_coin_keywords):
    # Test with Bitcoin mentions
    text1 = "Bitcoin is going up"
    content1 = "BTC to the moon!"
    coins1 = extract_mentioned_coins(text1, content1, test_coin_keywords)
    assert 'BTC' in coins1
    
    # Test with multiple coin mentions
    text2 = "ETH vs BTC"
    content2 = "Ethereum and Bitcoin comparison"
    coins2 = extract_mentioned_coins(text2, content2, test_coin_keywords)
    assert 'BTC' in coins2
    assert 'ETH' in coins2
    
    # Test with no coin mentions
    text3 = "Market analysis"
    content3 = "The crypto market is volatile"
    coins3 = extract_mentioned_coins(text3, content3, test_coin_keywords)
    assert coins3 == ''

# Test determine_sentiment function with parameterized inputs
@pytest.mark.parametrize("score, expected_sentiment", [
    (0.5, 'Positive'),
    (0.05, 'Positive'),  # Boundary condition
    (0.0, 'Neutral'),
    (-0.05, 'Negative'),  # Boundary condition
    (-0.5, 'Negative'),
])
def test_determine_sentiment(score, expected_sentiment):
    assert determine_sentiment(score) == expected_sentiment

# Test fetch_reddit_data function using VCR to record/replay API responses
@my_vcr.use_cassette()
def test_fetch_reddit_bitcoin_data(reddit_client, sentiment_analyzer, test_coin_keywords):
    """Test fetching Bitcoin-related data from Reddit."""
    # Use a smaller set of keywords just for Bitcoin for this test
    btc_keywords = {'BTC': test_coin_keywords['BTC']}
    
    # Run the function with real API (or recorded responses)
    result = fetch_reddit_data(reddit_client, 'Bitcoin', sentiment_analyzer, btc_keywords)
    
    # Validate the results
    assert isinstance(result, list)
    
    # We should get some results (the exact number depends on the API response)
    assert len(result) > 0
    
    # Check the structure of the results
    for post_data in result:
        # All posts should mention Bitcoin
        assert 'BTC' in post_data['coins']
        
        # Check the data structure
        assert 'id' in post_data and post_data['id'].startswith('RD_')
        assert 'domain' in post_data and post_data['domain'] == 'reddit.com'
        assert 'title' in post_data and isinstance(post_data['title'], str)
        assert 'published_at' in post_data and isinstance(post_data['published_at'], datetime)
        assert 'url' in post_data and post_data['url'].startswith('https://www.reddit.com/')
        assert 'sentiment' in post_data and post_data['sentiment'] in ['Positive', 'Neutral', 'Negative']

# Test with a different subreddit
@my_vcr.use_cassette()
def test_fetch_reddit_crypto_data(reddit_client, sentiment_analyzer, test_coin_keywords):
    """Test fetching general crypto data from the CryptoCurrency subreddit."""
    # Use both BTC and ETH keywords for this test
    result = fetch_reddit_data(reddit_client, 'CryptoCurrency', sentiment_analyzer, test_coin_keywords)
    
    # Basic validation
    assert isinstance(result, list)
    
    # We should get some results
    assert len(result) > 0
    
    # Check if we have both Bitcoin and Ethereum mentions in the results
    coins_mentioned = set()
    for post_data in result:
        coins = post_data['coins'].split(',')
        coins_mentioned.update(coins)
    
    # We should have at least one of our test coins
    assert len(coins_mentioned.intersection({'BTC', 'ETH'})) > 0

# You can add more specific tests for different scenarios 