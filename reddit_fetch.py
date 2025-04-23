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


def fetch_posts(
    reddit: praw.Reddit,
    subreddit_name: str,
    analyzer: SentimentIntensityAnalyzer,
    coin_keywords: Dict[str, List[str]],
    search_terms: List[str],
    limit: int = 100,
    sort_types: List[str] = ['hot', 'new', 'top'],
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

    processed_posts: List[ProcessedSubmission] = []
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

                processed_posts.append(process_reddit_submission(submission, analyzer, coin_keywords))
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
    config: Config
) -> List[ProcessedSubmission]:
    """
    Fetch and analyze posts related to specific coins from a subreddit
    """
    # Use coin names as search terms
    search_terms: List[str] = list(config.coin_keywords.keys())
    return fetch_posts(
        reddit,
        subreddit_name,
        analyzer,
        config.coin_keywords,
        search_terms=search_terms,
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

    # Convert to DataFrame
    df: pd.DataFrame = pd.DataFrame([
        {**post.model_dump(exclude={'coins', 'url'}),
         'coins': ",".join(post.coins),
         'url': str(post.url)}
        for post in posts
    ])

    # Check for existing IDs to avoid duplicates
    existing_ids_query = text("SELECT id FROM sentiment_data")
    existing_ids = pd.read_sql_query(existing_ids_query, engine)['id'].values

    # Filter out already existing posts
    print(f"Total posts fetched: {len(df)}")
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
    # Initialize VADER Sentiment Analyzer
    analyzer: SentimentIntensityAnalyzer = SentimentIntensityAnalyzer()

    # Initialize Reddit API connection
    reddit: praw.Reddit = setup_reddit()

    # Load configuration

    # Fetch data from all subreddits
    all_posts = fetch_all_subreddit_data(
        reddit,
        analyzer,
        config
    )

    # Store data in database
    engine: Engine = get_engine(config.db_path)
    store_submissions_in_database(all_posts, engine)


if __name__ == "__main__":
    main(load_config('config.yaml'))
