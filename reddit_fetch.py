import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import praw  # type: ignore [import-untyped]
from pydantic import BaseModel, HttpUrl
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore [import-untyped]

from config import Config, load_config
from database import SentimentData, get_engine, get_session

# Set up logging
logging.basicConfig(
    filename='coin_detection.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ProcessedSubmission(BaseModel):
    id: str                      # e.g., "RD_1jzplfx"
    domain: str                  # Always "reddit.com"
    title: str                   # Copied from original submission
    coins: List[str]             # Extracted coins (e.g., ['BTC', 'ETH'])
    published_at: datetime       # Datetime from UNIX timestamp
    url: HttpUrl                 # Full Reddit post URL
    sentiment: float               # VADER sentiment score from -1 to 1


def setup_reddit() -> praw.Reddit:
    """
    Initialize Reddit API connection
    """

    # Check for required environment variables
    required_env_vars: List[str] = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]
    missing_vars: List[str] = [var for var in required_env_vars if var not in os.environ]
    if missing_vars:
        raise ValueError(f"Error: Missing required environment variables: {', '.join(missing_vars)}")

    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"]
    )


def extract_mentioned_coins(title: str, content: str, coin_keywords: Dict[str, List[str]]) -> List[str]:
    """Config
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

    logging.debug(f"Final extracted coins: {','.join(mentioned_coins)}")
    return mentioned_coins


def process_reddit_submission(
    submission: praw.models.Submission,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]]
) -> ProcessedSubmission:
    """
    Process a single reddit.submission object and extract the necessary data

    Parameters:
    - submission: praw.models.Submission instance
    - analyzer: sentiment analyzer instance
    - coin_keywords: dictionary of coin keywords

    Returns:
    - ProcessedSubmission
    """
    full_text: str = f"{submission.title} {submission.selftext}"
    logging.debug(f"Analyzing text: {full_text[:200]}...")

    sentiment_scores: Dict[str, float] = analyzer.polarity_scores(full_text)

    # Create post entry
    return ProcessedSubmission(
        id=f"RD_{submission.id}",
        domain='reddit.com',
        title=submission.title,
        coins=extract_mentioned_coins(submission.title, submission.selftext, coin_keywords),
        published_at=datetime.fromtimestamp(submission.created_utc),
        url=HttpUrl(f"https://www.reddit.com{submission.permalink}"),
        sentiment=sentiment_scores['compound']
    )


def _fetch_posts(
    subreddit: praw.models.Subreddit,
    fetch_method: str,
    query_param: str,
    limit: int,
    time_filter: str,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]],
) -> List[ProcessedSubmission]:
    """Generic function to fetch posts by either sort type or search term."""
    processed: List[ProcessedSubmission] = []
    try:
        # Get submissions based on fetch method
        if fetch_method == 'sort':
            if query_param == 'hot':
                submissions = subreddit.hot(limit=limit)
            elif query_param == 'new':
                submissions = subreddit.new(limit=limit)
            elif query_param == 'top':
                submissions = subreddit.top(time_filter=time_filter, limit=limit)
            elif query_param == 'rising':
                submissions = subreddit.rising(limit=limit)
            else:
                logging.warning(f"Unknown sort type skipped: {query_param}")
                return []
        elif fetch_method == 'search':
            submissions = subreddit.search(query_param, time_filter=time_filter, limit=limit)
        else:
            logging.warning(f"Unknown fetch method: {fetch_method}")
            return []

        # Process submissions
        for submission in submissions:
            if not submission.is_self:  # Skip non-text posts
                continue
            processed.append(process_reddit_submission(submission, analyzer, coin_keywords))
            time.sleep(0.1)
    except Exception as e:
        logging.error(f"Error fetching posts via {fetch_method} ({query_param}) from r/{subreddit.display_name}: {e}")
    return processed


def fetch_posts(
    reddit: praw.Reddit,
    subreddit_name: str,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]],
    search_terms: List[str],
    limit: int = 100,
    sort_types: List[str] | None = None,
    time_filter: str = 'week'
) -> List[ProcessedSubmission]:
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
    if sort_types is None:
        sort_types = ['hot', 'new', 'top']

    subreddit: praw.models.Subreddit = reddit.subreddit(subreddit_name)

    # Define fetch operations with their parameters
    fetch_operations = [
        # Sort type operations
        *[('sort', sort_type) for sort_type in sort_types],

        # Search term operations
        *[('search', term) for term in search_terms]
    ]

    # Execute all fetch operations and collect the results
    processed_posts = [
        post
        for method, param in fetch_operations
        for post in _fetch_posts(subreddit, method, param, limit, time_filter, analyzer, coin_keywords)
    ]

    return processed_posts


def fetch_reddit_data(
    reddit: praw.Reddit,
    subreddit_name: str,
    analyzer: SentimentIntensityAnalyzer,
    config: Config
) -> List[ProcessedSubmission]:
    """
    Fetch and analyze posts related to specific coins from a subreddit
    """
    return fetch_posts(
        reddit,
        subreddit_name,
        analyzer,
        config.coin_keywords,
        search_terms=list(config.coin_keywords.keys()),
        sort_types=['hot', 'new', 'top'],
        limit=config.posts_limit
    )


def fetch_all_subreddit_data(
    reddit: praw.Reddit,
    analyzer: SentimentIntensityAnalyzer,
    config: Config
) -> List[ProcessedSubmission]:
    """
    Fetch data from all specified subreddits.

    Parameters:
    - reddit: praw.Reddit instance
    - subreddits: List of subreddit names to fetch from
    - analyzer: SentimentIntensityAnalyzer instance
    - coin_keywords: Dictionary of coin keywords

    Returns:
    - List of ProcessedSubmission objects
    """
    all_posts: List[ProcessedSubmission] = []

    for subreddit_name in config.subreddits:
        print(f"Fetching data from r/{subreddit_name}...")
        posts = fetch_reddit_data(
            reddit, subreddit_name, analyzer, config
        )
        all_posts.extend(posts)
        print(f"Fetched {len(posts)} posts from r/{subreddit_name}")

    return all_posts


def store_submissions_in_database(
    posts: List[ProcessedSubmission],
    engine: Engine
) -> int:
    """
    Store submission data in the database.

    Parameters:
    - posts: List of ProcessedSubmission objects
    - engine: SQLAlchemy Engine instance

    Returns:
    - Number of new posts added to the database
    """
    if not posts:
        print("No posts were fetched.")
        return 0

    # Filter duplicate posts by ID (keep first occurrence only)
    seen_ids: set[str] = set()
    unique_posts: List[ProcessedSubmission] = []

    for post in posts:
        if post.id not in seen_ids:
            seen_ids.add(post.id)
            unique_posts.append(post)

    # Convert to DataFrame
    df: pd.DataFrame = pd.DataFrame([
        {**post.model_dump(exclude={'coins', 'url'}),
         'coins': ",".join(post.coins),
         'url': str(post.url)}
        for post in unique_posts
    ])

    # Check for existing IDs to avoid duplicates
    existing_ids_query = text("SELECT id FROM sentiment_data")
    existing_ids = pd.read_sql_query(existing_ids_query, engine)['id'].values

    # Filter out already existing posts
    print(f"Total posts fetched: {len(posts)}")
    print(f"Unique posts after removing duplicates: {len(unique_posts)}")
    new_df: pd.DataFrame = df[~df['id'].isin(existing_ids)]
    print(f"New posts to add: {len(new_df)}")

    if new_df.empty:
        print("No new posts to add.")
        return 0

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
        return len(new_records)
    except Exception as e:
        session.rollback()
        print(f"Error adding posts to database: {e}")
        return 0
    finally:
        session.close()


def main(config: Config) -> None:
    """
    Main function to fetch Reddit data and store it in the database.
    """

    # Fetch data from all subreddits
    all_posts = fetch_all_subreddit_data(
        setup_reddit(),
        SentimentIntensityAnalyzer(),
        config
    )

    # Store data in database
    store_submissions_in_database(all_posts, get_engine(config.db_path))


if __name__ == "__main__":
    main(load_config('config.yaml'))
