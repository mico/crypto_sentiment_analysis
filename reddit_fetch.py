import os
import praw
import pandas as pd
import sqlite3
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time

def initialize_database(db_path='crypto_data.db'):
    """
    Create the database and required tables if they don't exist
    """
    # Check if database file exists
    db_exists = os.path.isfile(db_path)
    
    # Connect to the database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
        
    if not db_exists:
        print(f"Database file {db_path} not found. Creating new database...")
        
        cursor = conn.cursor()
        # Create the crypto_news_sentiment table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_news_sentiment (
            "index" INTEGER,
            "id" INTEGER,
            "domain" TEXT,
            "title" TEXT,
            "coins" TEXT,
            "published_at" TEXT,
            "url" TEXT,
            "sentiment" TEXT
        )
        ''')
        
        # Create any indexes that might improve performance
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_coins ON crypto_news_sentiment(coins)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sentiment ON crypto_news_sentiment(sentiment)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_published_at ON crypto_news_sentiment(published_at)
        ''')
        
        conn.commit()
        print("Database initialized successfully.")
    else:
        print(f"Using existing database: {db_path}")

    return conn

def setup_reddit():
    """
    Initialize Reddit API connection
    """
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"]
    )

def get_crypto_subreddits():
    """
    List of cryptocurrency-related subreddits to monitor
    """
    return [
        "CryptoCurrency",
        "Bitcoin",
        "ethereum",
        "CryptoMarkets",
        "binance",
        "SatoshiStreetBets",
        # Add these additional subreddits
        "altcoin",
        "CryptoMoonShots",
        "solana",
        "Ripple",
        "cardano",
        "dogecoin",
        "CryptoTechnology",
        "CryptoNews",
        "ethtrader"
    ]

def determine_sentiment(compound_score):
    """
    Convert VADER compound score to categorical sentiment
    VADER compound score ranges from -1 (most negative) to +1 (most positive)
    """
    if compound_score >= 0.05:
        return 'Positive'
    elif compound_score <= -0.05:
        return 'Negative'
    else:
        return 'Neutral'

def extract_mentioned_coins(title, content, coin_keywords):
    """
    Extract mentioned cryptocurrency symbols from text
    """
    text = f"{title} {content}".upper()
    mentioned_coins = []
    
    for coin, keywords in coin_keywords.items():
        if any(keyword in text for keyword in keywords):
            mentioned_coins.append(coin)
    
    return ','.join(mentioned_coins) if mentioned_coins else ''

def get_coin_keywords():
    """
    Dictionary of coins and their related keywords to search for
    """
    return {
        'BTC': ['BTC', 'BITCOIN', 'BTCUSD', 'SATS', 'SATOSHI', 'NAKAMOTO'],
        'ETH': ['ETH', 'ETHEREUM', 'ETHUSD', 'ETHBTC', 'VITALIK', 'BUTERIN', 'GWEI'],
        'BNB': ['BNB', 'BINANCE COIN', 'BINANCE CHAIN', 'CZ'],
        'SOL': ['SOL', 'SOLANA', 'SOLUSD', 'SOLBTC'],
        'XRP': ['XRP', 'RIPPLE', 'XRPUSD', 'GARLINGHOUSE'],
        'ADA': ['ADA', 'CARDANO', 'HOSKINSON', 'ADAUSD'],
        'DOGE': ['DOGE', 'DOGECOIN', 'DOGEUSD', 'SHIBA', 'MUSK'],
        'DOT': ['DOT', 'POLKADOT', 'DOTUSD', 'GAVIN WOOD'],
        'AVAX': ['AVAX', 'AVALANCHE', 'AVAXUSD'],
        'MATIC': ['MATIC', 'POLYGON', 'MATICUSD']
    }

def fetch_reddit_data(reddit, subreddit_name, analyzer, coin_keywords):
    """
    Fetch and analyze posts from a specific subreddit
    """
    subreddit = reddit.subreddit(subreddit_name)
    posts_data = []
    
    # Search for posts related to each coin
    for coin in coin_keywords.keys():
        try:
            # Get hot posts and new posts
            for post in subreddit.search(coin, limit=50, sort='hot'):
                # Combine title and selftext for better context
                full_text = f"{post.title} {post.selftext}"
                sentiment_scores = analyzer.polarity_scores(full_text)
                
                # Create post entry
                post_data = {
                    'id': f"RD_{post.id}",
                    'domain': 'reddit.com',
                    'title': post.title,
                    'coins': extract_mentioned_coins(post.title, post.selftext, coin_keywords),
                    'published_at': datetime.fromtimestamp(post.created_utc),
                    'url': f"https://www.reddit.com{post.permalink}",
                    'sentiment': determine_sentiment(sentiment_scores['compound'])
                }
                
                # Only add posts that have mentioned coins
                if post_data['coins']:
                    posts_data.append(post_data)
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"Error fetching data for {coin} in {subreddit_name}: {e}")
            continue
    
    return posts_data

def main():
    # Check for required environment variables
    required_env_vars = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Initialize Reddit and VADER
    reddit = setup_reddit()
    analyzer = SentimentIntensityAnalyzer()
    coin_keywords = get_coin_keywords()
    db_path = 'crypto_data.db'
    conn = initialize_database(db_path)
    
    # Get existing Reddit post IDs to avoid duplicates
    query = "SELECT id FROM crypto_news_sentiment WHERE domain='reddit.com'"
    existing_ids = pd.read_sql_query(query, conn)['id'].values
    
    all_posts_data = []
    
    # Fetch data from each subreddit
    for subreddit_name in get_crypto_subreddits():
        print(f"Fetching data from r/{subreddit_name}...")
        posts_data = fetch_reddit_data(reddit, subreddit_name, analyzer, coin_keywords)
        all_posts_data.extend(posts_data)
        time.sleep(5)  # Rate limiting between subreddits
    
    if all_posts_data:
        # Convert to DataFrame
        df = pd.DataFrame(all_posts_data)
        
        # Remove duplicates and posts we already have
        df = df.drop_duplicates(subset=['id'])
        df = df[~df['id'].isin(existing_ids)]
        
        # Store in database
        if not df.empty:
            df.to_sql('crypto_news_sentiment', conn, if_exists='append', index=False)
            print(f"Added {len(df)} new records to database")
        else:
            print("No new data to add")
    
    conn.close()

if __name__ == "__main__":
    main() 