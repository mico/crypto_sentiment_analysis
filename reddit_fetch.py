import os
import praw # type: ignore [import]
import pandas as pd
import sqlite3
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer # type: ignore [import]
import time
import re
import logging
import yaml  # type: ignore [import]

# Set up logging
logging.basicConfig(
    filename='coin_detection.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

def load_config(config_path='config.yaml'):
    """
    Load configuration from YAML file
    
    Parameters:
    - config_path: Path to the YAML config file
    
    Returns:
    - dict: Configuration dictionary
    """
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML config: {e}")
        raise

def get_crypto_subreddits(config_path='config.yaml'):
    """
    List of cryptocurrency-related subreddits to monitor from config
    """
    config = load_config(config_path)
    return config['subreddits']

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
    Extract mentioned cryptocurrency symbols from text with improved precision
    """
    text = f"{title} {content}".upper()
    mentioned_coins = []
    
    for coin, keywords in coin_keywords.items():
        # Check if any keyword is found as a whole word
        found = False
        for keyword in keywords:
            logging.debug(f"Matched {coin} with keyword '{keyword}'")
            # Add word boundary check (space, punctuation, or start/end of text)
            # This regex pattern looks for the keyword surrounded by non-alphanumeric chars or text boundaries
            pattern = r'(^|[^\w])' + re.escape(keyword) + r'($|[^\w])'
            if re.search(pattern, text):
                found = True
                break
                
        if found:
            mentioned_coins.append(coin)
    
    result = ','.join(mentioned_coins) if mentioned_coins else ''
    logging.debug(f"Final extracted coins: {result}")
    return result

def get_coin_keywords(config_path='config.yaml'):
    """
    Dictionary of coins and their related keywords to search for from config
    """
    config = load_config(config_path)
    return config['coin_keywords']

def process_reddit_submission(submission, analyzer, coin_keywords):
    """
    Process a single reddit.submission object and extract the necessary data
    
    Parameters:
    - submission: praw.models.Submission instance
    - analyzer: sentiment analyzer instance
    - coin_keywords: dictionary of coin keywords
    
    Returns:
    - dict: post data dictionary with sentiment and coin information
    """
    full_text = f"{submission.title} {submission.selftext}"
    logging.debug(f"Analyzing text: {full_text[:200]}...")

    sentiment_scores = analyzer.polarity_scores(full_text)
    
    # Create post entry
    post_data = {
        'id': f"RD_{submission.id}",
        'domain': 'reddit.com',
        'title': submission.title,
        'coins': extract_mentioned_coins(submission.title, submission.selftext, coin_keywords),
        'published_at': datetime.fromtimestamp(submission.created_utc),
        'url': f"https://www.reddit.com{submission.permalink}",
        'sentiment': determine_sentiment(sentiment_scores['compound'])
    }
    
    return post_data

def fetch_posts(reddit, subreddit_name, analyzer, coin_keywords, search_terms, limit=100, 
               sort_types=None, time_filter='week'):
    """
    Generic function to fetch and analyze posts from a subreddit based on search terms
    
    Parameters:
    - reddit: praw Reddit instance
    - subreddit_name: name of the subreddit to search
    - analyzer: sentiment analyzer instance
    - coin_keywords: dictionary of coin keywords
    - search_terms: list of terms to search for
    - limit: maximum number of posts to fetch per term/sort
    - sort_types: list of sort methods (defaults to ['hot'] if None)
    - time_filter: time filter for searches
    """
    if sort_types is None:
        sort_types = ['hot']
        
    subreddit = reddit.subreddit(subreddit_name)
    posts_data = []
    request_count = 0
    
    for term in search_terms:
        try:
            for sort_type in sort_types:
                request_count += 1
                # Reset timer if approaching rate limit
                if request_count >= 50:
                    print(f"Approaching rate limit, pausing for 10 seconds...")
                    time.sleep(10)
                    request_count = 0
                
                for post in subreddit.search(term, limit=limit, sort=sort_type, time_filter=time_filter):
                    post_data = process_reddit_submission(post, analyzer, coin_keywords)
                    
                    # Only add posts that have mentioned coins
                    if post_data['coins']:
                        posts_data.append(post_data)
                
                # Small pause between requests
                time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching data for term '{term}' in {subreddit_name}: {e}")
            continue
    
    return posts_data

def fetch_reddit_data(reddit, subreddit_name, analyzer, coin_keywords):
    """
    Fetch and analyze posts related to specific coins from a subreddit
    """
    # Use coin names as search terms
    search_terms = coin_keywords.keys()
    return fetch_posts(
        reddit, 
        subreddit_name, 
        analyzer, 
        coin_keywords, 
        search_terms=search_terms,
        sort_types=['hot', 'new', 'top'],
        limit=100
    )

def fetch_general_crypto_posts(reddit, subreddit_name, analyzer, coin_keywords, config_path='config.yaml'):
    """
    Fetch general crypto discussion posts that might not mention specific coins
    """
    config = load_config(config_path)
    general_terms = config['general_terms']
    return fetch_posts(
        reddit, 
        subreddit_name, 
        analyzer, 
        coin_keywords, 
        search_terms=general_terms,
        sort_types=['hot', 'new', 'top'],
        limit=75
    )

def main():
    # Check for required environment variables
    required_env_vars = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Initialize Reddit and VADER
    reddit = setup_reddit()
    analyzer = SentimentIntensityAnalyzer()
    config_path = 'config.yaml'
    coin_keywords = get_coin_keywords(config_path)
    db_path = 'crypto_data.db'
    conn = initialize_database(db_path)
    
    # Get existing Reddit post IDs to avoid duplicates
    query = "SELECT id FROM crypto_news_sentiment WHERE domain='reddit.com'"
    existing_ids = pd.read_sql_query(query, conn)['id'].values
    
    all_posts_data = []
    
    # Fetch data from each subreddit
    for subreddit_name in get_crypto_subreddits(config_path):
        print(f"Fetching data from r/{subreddit_name}...")
        posts_data = fetch_reddit_data(reddit, subreddit_name, analyzer, coin_keywords)
        all_posts_data.extend(posts_data)
        time.sleep(5)  # Rate limiting between subreddits
    
    for subreddit_name in get_crypto_subreddits(config_path):
        print(f"Fetching general crypto discussions from r/{subreddit_name}...")
        general_posts = fetch_general_crypto_posts(reddit, subreddit_name, analyzer, coin_keywords, config_path)
        all_posts_data.extend(general_posts)
        time.sleep(3)  # Rate limiting
    
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