#!/usr/bin/env python
import os
import sys
import time
from typing import Any, Dict, List

import praw  # type: ignore [import-untyped]
import yaml

from reddit_fetch import setup_reddit

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def extract_submission_by_id(
    reddit: praw.Reddit,
    submission_id: str,
    output_dir: str = 'tests/fixtures/submissions'
) -> None:
    """
    Extract a specific submission by ID and save it as a YAML file

    Parameters:
    - reddit: praw.Reddit instance
    - submission_id: ID of the submission to extract
    - output_dir: directory to save the YAML file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Get the submission
        submission: praw.models.Submission = reddit.submission(id=submission_id)

        # Extract all necessary attributes
        submission_data: Dict[str, Any] = {
            'id': submission.id,
            'title': submission.title,
            'selftext': submission.selftext,
            'created_utc': submission.created_utc,
            'permalink': submission.permalink,
            'url': submission.url,
            'author': str(submission.author) if submission.author else None,
            'subreddit': submission.subreddit.display_name,
            'score': submission.score,
            'upvote_ratio': getattr(submission, 'upvote_ratio', 0),
            'num_comments': submission.num_comments,
        }

        # Save to YAML file
        output_file: str = os.path.join(output_dir, f"{submission_id}.yaml")
        with open(output_file, 'w') as f:
            yaml.dump(submission_data, f, default_flow_style=False)

        print(f"Saved submission {submission_id} to {output_file}")

    except Exception as e:
        print(f"Error extracting data for submission {submission_id}: {e}")


def extract_multiple_submissions(
    submission_ids: List[str],
    output_dir: str = 'tests/fixtures/submissions'
) -> None:
    """
    Extract multiple submissions by ID and save them as YAML files

    Parameters:
    - submission_ids: list of submission IDs to extract
    - output_dir: directory to save the YAML files
    """
    reddit: praw.Reddit = setup_reddit()

    for submission_id in submission_ids:
        extract_submission_by_id(reddit, submission_id, output_dir)
        time.sleep(1)  # Avoid rate limiting


if __name__ == "__main__":
    # List of submission IDs to extract
    submission_ids: List[str] = [
        '1jzplfx',  # BTC Maxi's - Bitcoin subreddit - Positive
        '1k0fod8',  # Gold vs BTC - CryptoCurrency subreddit - Positive
        '1kbr8vn',  # ETH gas fees issue - Ethereum subreddit - Negative
        '1j5m2pq',  # SOL wallet question - Solana subreddit - Neutral
    ]

    # You can also pass IDs via command line
    if len(sys.argv) > 1:
        submission_ids = sys.argv[1:]

    try:
        extract_multiple_submissions(submission_ids)
        print("Done extracting submissions!")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure your environment variables are set: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")
        sys.exit(1)
