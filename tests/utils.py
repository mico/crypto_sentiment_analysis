import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, HttpUrl


class SubmissionData(BaseModel):
    author: str
    created_utc: float
    id: str
    num_comments: int
    permalink: str
    score: int
    selftext: Optional[str]  # Sometimes it might be empty or None
    subreddit: str
    title: str
    upvote_ratio: float
    url: HttpUrl  # Ensures it's a valid URL


def load_test_submission(submission_id: str, fixtures_dir: str = 'tests/fixtures/submissions') -> SubmissionData:
    """
    Load a test submission from a YAML file

    Parameters:
    - submission_id: ID of the submission to load
    - fixtures_dir: directory containing submission YAML files

    Returns:
    - object: A submission-like object with attributes from the YAML file
    """

    yaml_path = os.path.join(fixtures_dir, f"{submission_id}.yaml")

    try:
        with open(yaml_path, 'r') as f:
            submission_data = SubmissionData(**yaml.safe_load(f))

        # Create a simple object that mimics a Reddit submission
        # class TestSubmission:
        #     def __init__(self, data: SubmissionData) -> None:
        #         self.__dict__.update(data)

        #         # Create a simple Subreddit-like object
        #         if 'subreddit' in data and isinstance(data['subreddit'], str):
        #             self.subreddit = type('Subreddit', (), {'display_name': data['subreddit']})()

        return submission_data
    except FileNotFoundError:
        raise ValueError(f"Submission {submission_id} not found in fixtures directory")


def load_test_env(env_file: str = ".env.testing") -> None:
    """
    Load environment variables from .env.testing file if it exists.

    Args:
        env_file: The environment file to load, defaults to .env.testing
    """
    from dotenv import load_dotenv

    # Get the project root directory
    project_root = Path(__file__).parent.parent
    env_path = project_root / env_file

    # Load environment variables from .env.testing if it exists
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=True)
