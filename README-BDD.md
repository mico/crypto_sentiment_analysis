# Behavior-Driven Development (BDD) Tests

This project uses pytest-bdd to implement behavior-driven development tests for the cryptocurrency sentiment analysis functionality.

## Overview

BDD focuses on describing the behavior of the system from a user perspective, using scenarios written in a natural language format (Gherkin). The BDD approach helps to:

- Document the expected behavior in a human-readable format
- Ensure test coverage aligns with expected behaviors
- Facilitate communication between technical and non-technical stakeholders

## Test Structure

The BDD tests are organized as follows:

1. **Feature files** (`features/*.feature`): Define scenarios using Gherkin syntax
2. **Step definitions** (`test_reddit_fetch_bdd.py`): Python code that implements the steps in the feature files

### Feature Files

There are three main feature files:

- `features/coin_extraction.feature`: Tests for detecting cryptocurrency mentions in text
- `features/sentiment_analysis.feature`: Tests for sentiment classification
- `features/reddit_data_fetching.feature`: Tests for fetching and processing Reddit data

### Example Feature

```gherkin
Feature: Cryptocurrency Mention Extraction
  As a crypto sentiment analyzer
  I want to extract cryptocurrency mentions from text
  So that I can track which cryptocurrencies are being discussed

  Background:
    Given a set of cryptocurrency keywords

  Scenario: Extract Bitcoin mentions
    When I analyze the title "Bitcoin is going up" and content "BTC to the moon!"
    Then the extracted coins should include "BTC"
```

## Running the Tests

To run the BDD tests, use pytest with the BDD test file:

```bash
python -m pytest test_reddit_fetch_bdd.py -v
```

### Options

- `-v`: Verbose output showing each test
- `-k "keyword"`: Run only tests matching the keyword
- `--gherkin-terminal-reporter`: Generate Gherkin-style output

## VCR Integration

The tests integrate with VCR.py to record and replay HTTP interactions for Reddit API calls. This:

- Makes tests faster after the first run
- Reduces API rate limiting issues
- Makes tests deterministic

Tests marked with the `@vcr` tag use recorded cassettes from the `fixtures/vcr_cassettes` directory.

## Adding New Tests

To add a new BDD test:

1. Create or modify a feature file in the `features/` directory
2. Implement step definitions in `test_reddit_fetch_bdd.py` 
3. Use `target_fixture` in your step definitions to pass context between steps

### Example Step Definition

```python
@when(parsers.parse('I analyze the title "{title}" and content "{content}"'), target_fixture="extraction_data")
def analyze_text(title, content, coin_keywords):
    """Analyze text for coin mentions and store input for later assertions."""
    return {
        "title": title, 
        "content": content, 
        "coin_keywords": coin_keywords,
        "result": extract_mentioned_coins(title, content, coin_keywords)
    }
```

## Dependencies

- pytest-bdd: BDD plugin for pytest
- vcr.py: HTTP interaction recording

Install dependencies with:

```bash
pip install pytest-bdd vcrpy
``` 