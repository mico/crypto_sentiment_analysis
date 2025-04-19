import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import praw  # type: ignore [import]
import yaml
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore [import]

from database import get_engine, get_session, SentimentData

# Set up logging
logging.basicConfig(
    filename='coin_detection.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def setup_reddit() -> praw.Reddit:
    """
    Initialize Reddit API connection
    """
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"]
    )


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
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


def get_crypto_subreddits(config_path: str = 'config.yaml') -> List[str]:
    """
    List of cryptocurrency-related subreddits to monitor from config
    """
    config: Dict[str, Any] = load_config(config_path)
    return config['subreddits']


def determine_sentiment(compound_score: float) -> str:
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


def extract_mentioned_coins(title: str, content: str, coin_keywords: Dict[str, List[str]]) -> str:
    """
    Extract mentioned cryptocurrency symbols from text with improved precision
    """
    text: str = f"{title} {content}".upper()
    mentioned_coins: List[str] = []

    for coin, keywords in coin_keywords.items():
        # Check if any keyword is found as a whole word
        found: bool = False
        for keyword in keywords:
            logging.debug(f"Matched {coin} with keyword '{keyword}'")
            # Add word boundary check (space, punctuation, or start/end of text)
            # This regex pattern looks for the keyword surrounded by non-alphanumeric chars
            # or text boundaries
            pattern: str = r'(^|[^\w])' + re.escape(keyword) + r'($|[^\w])'
            if re.search(pattern, text):
                found = True
                break

        if found:
            mentioned_coins.append(coin)

    result: str = ','.join(mentioned_coins) if mentioned_coins else ''
    logging.debug(f"Final extracted coins: {result}")
    return result


def get_coin_keywords(config_path: str = 'config.yaml') -> Dict[str, List[str]]:
    """
    Dictionary of coins and their related keywords to search for from config
    """
    config: Dict[str, Any] = load_config(config_path)
    return config['coin_keywords']


def process_reddit_submission(
    submission: praw.models.Submission,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Process a single reddit.submission object and extract the necessary data

    Parameters:
    - submission: praw.models.Submission instance
    - analyzer: sentiment analyzer instance
    - coin_keywords: dictionary of coin keywords

    Returns:
    - dict: post data dictionary with sentiment and coin information
    """
    full_text: str = f"{submission.title} {submission.selftext}"
    logging.debug(f"Analyzing text: {full_text[:200]}...")

    sentiment_scores: Dict[str, float] = analyzer.polarity_scores(full_text)

    # Create post entry
    post_data: Dict[str, Any] = {
        'id': f"RD_{submission.id}",
        'domain': 'reddit.com',
        'title': submission.title,
        'coins': extract_mentioned_coins(submission.title, submission.selftext, coin_keywords),
        'published_at': datetime.fromtimestamp(submission.created_utc),
        'url': f"https://www.reddit.com{submission.permalink}",
        'sentiment': determine_sentiment(sentiment_scores['compound'])
    }

    return post_data


def fetch_posts(
    reddit: praw.Reddit,
    subreddit_name: str,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]],
    search_terms: List[str],
    limit: int = 100,
    sort_types: Optional[List[str]] = None,
    time_filter: str = 'week'
) -> List[Dict[str, Any]]:
    """
    Generic function to fetch and analyze posts from a subreddit based on search terms

    Parameters:
    - reddit: praw Reddit instance
    - subreddit_name: name of the subreddit to search
    - analyzer: sentiment analyzer instance
    - coin_keywords: dictionary of coin keywords
    - search_terms: list of terms to search for
    - limit: maximum number of posts to fetch per search term and sort type
    - sort_types: list of sort types to use (hot, new, top, etc.)
    - time_filter: time filter for relevance (day, week, month, year, all)

    Returns:
    - List of processed post data dictionaries
    """
    # Default sort types if none provided
    if sort_types is None:
        sort_types = ['hot', 'new', 'top']

    processed_posts: List[Dict[str, Any]] = []
    subreddit: praw.models.Subreddit = reddit.subreddit(subreddit_name)

    # Process sort-based posts
    for sort_type in sort_types:
        try:
            if sort_type == 'hot':
                submissions = subreddit.hot(limit=limit)
            elif sort_type == 'new':
                submissions = subreddit.new(limit=limit)
            elif sort_type == 'top':
                submissions = subreddit.top(time_filter=time_filter, limit=limit)
            elif sort_type == 'rising':
                submissions = subreddit.rising(limit=limit)
            else:
                continue  # Skip unknown sort types

            # Process each submission
            for submission in submissions:
                # Skip non-text posts
                if not submission.is_self:
                    continue

                result = process_reddit_submission(submission, analyzer, coin_keywords)
                processed_posts.append(result)
                time.sleep(0.1)  # Avoid hitting API limits

        except Exception as e:
            logging.error(f"Error fetching {sort_type} posts from r/{subreddit_name}: {e}")

    # Process search-based posts
    for term in search_terms:
        try:
            search_results = subreddit.search(
                term, time_filter=time_filter, limit=limit
            )

            for submission in search_results:
                # Skip non-text posts
                if not submission.is_self:
                    continue

                result = process_reddit_submission(
                    submission, analyzer, coin_keywords
                )
                processed_posts.append(result)
                time.sleep(0.1)  # Avoid hitting API limits

        except Exception as e:
            logging.error(f"Error searching for '{term}' in r/{subreddit_name}: {e}")

    return processed_posts


def fetch_reddit_data(
    reddit: praw.Reddit,
    subreddit_name: str,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """
    Fetch and analyze posts related to specific coins from a subreddit
    """
    # Use coin names as search terms
    search_terms: List[str] = list(coin_keywords.keys())
    return fetch_posts(
        reddit,
        subreddit_name,
        analyzer,
        coin_keywords,
        search_terms=search_terms,
        sort_types=['hot', 'new', 'top'],
        limit=100
    )


def fetch_general_crypto_posts(
    reddit: praw.Reddit,
    subreddit_name: str,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]],
    config_path: str = 'config.yaml'
) -> List[Dict[str, Any]]:
    """Fetch general crypto discussion posts that might not mention specific coins.

    Parameters:
    - reddit: praw Reddit instance
    - subreddit_name: name of the subreddit to search
    - analyzer: sentiment analyzer instance
    - coin_keywords: dictionary of coin keywords
    - config_path: path to configuration file

    Returns:
    - List of processed post data dictionaries
    """
    config: Dict[str, Any] = load_config(config_path)
    general_terms: List[str] = config['general_terms']
    return fetch_posts(
        reddit,
        subreddit_name,
        analyzer,
        coin_keywords,
        search_terms=general_terms,
        sort_types=['hot', 'new', 'top'],
        limit=75
    )


def main() -> None:
    # Check for required environment variables
    required_env_vars: List[str] = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]
    missing_vars: List[str] = [var for var in required_env_vars if var not in os.environ]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running.")
        return

    # Initialize VADER Sentiment Analyzer
    analyzer: SentimentIntensityAnalyzer = SentimentIntensityAnalyzer()

    # Initialize Reddit API connection
    reddit: praw.Reddit = setup_reddit()

    # Load coin keywords from config
    coin_keywords: Dict[str, List[str]] = get_coin_keywords()

    # Get list of subreddits to monitor
    subreddits: List[str] = get_crypto_subreddits()

    all_posts: List[Dict[str, Any]] = []

    for subreddit_name in subreddits:
        print(f"Fetching data from r/{subreddit_name}...")
        posts = fetch_reddit_data(
            reddit, subreddit_name, analyzer, coin_keywords
        )
        all_posts.extend(posts)
        print(f"Fetched {len(posts)} posts from r/{subreddit_name}")

    if all_posts:
        # Convert to DataFrame
        df: pd.DataFrame = pd.DataFrame(all_posts)

        # Check for existing IDs to avoid duplicates
        engine: Engine = get_engine()
        existing_ids_query = text("SELECT id FROM sentiment_data")
        existing_ids = pd.read_sql_query(existing_ids_query, engine)['id'].values

        # Filter out already existing posts
        print(f"Total posts fetched: {len(df)}")
        new_df: pd.DataFrame = df[~df['id'].isin(existing_ids)]
        print(f"New posts to add: {len(new_df)}")

        if not new_df.empty:
            # Insert new posts into database using SQLAlchemy
            new_records = new_df.to_dict('records')
            session: Session = get_session(engine)
            try:
                for record in new_records:
                    # Ensure all keys in record are strings to fix the linter error
                    record_dict: Dict[str, Any] = {str(k): v for k, v in record.items()}
                    sentiment_data = SentimentData(**record_dict)
                    session.add(sentiment_data)
                session.commit()
                print(f"Successfully added {len(new_records)} new posts to database")
            except Exception as e:
                session.rollback()
                print(f"Error adding posts to database: {e}")
            finally:
                session.close()
        else:
            print("No new posts to add.")
    else:
        print("No posts were fetched.")


if __name__ == "__main__":
    main()
