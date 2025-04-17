import os
import yaml

def load_test_submission(submission_id, fixtures_dir='tests/fixtures/submissions'):
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
            submission_data = yaml.safe_load(f)
            
        # Create a simple object that mimics a Reddit submission
        class TestSubmission:
            def __init__(self, data):
                self.__dict__.update(data)
                
                # Create a simple Subreddit-like object
                if 'subreddit' in data and isinstance(data['subreddit'], str):
                    self.subreddit = type('Subreddit', (), {'display_name': data['subreddit']})()
        
        return TestSubmission(submission_data)
    except FileNotFoundError:
        raise ValueError(f"Submission {submission_id} not found in fixtures directory") 