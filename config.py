from pydantic import BaseModel
from typing import Dict, List
import yaml
import logging


class Config(BaseModel):
    subreddits: List[str]
    coin_keywords: Dict[str, List[str]]
    general_terms: List[str]
    db_path: str
    posts_limit: int


def load_config(config_path: str = 'config.yaml') -> Config:
    """
    Load configuration from YAML file

    Parameters:
    - config_path: Path to the YAML config file

    Returns:
    - dict: Configuration dictionary
    """
    try:
        with open(config_path, 'r') as file:
            return Config(**yaml.safe_load(file))
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML config: {e}")
        raise
