Feature: Submission Analysis
  As a crypto sentiment analyzer
  I want to analyze specific Reddit submissions
  So that I can correctly identify coins and determine sentiment without API calls

  Background:
    Given a sentiment analyzer
    And a set of cryptocurrency keywords
    And I have loaded test submissions from fixtures

  Scenario Outline: Comprehensive submission analysis
    When I analyze the submission with ID "<submission_id>"
    Then the sentiment should be classified as "<expected_sentiment>"
    And the extracted coins should include "<expected_coins>"
    And the submission title should contain "<title_keyword>"
    And the submission should be from the "<subreddit>" subreddit

    Examples:
      | submission_id | expected_sentiment | expected_coins | title_keyword | subreddit      |
      | 1jzplfx       | 0.3                | BTC            | Maxi          | Bitcoin        |
      | 1k0fod8       | 0.7                | BTC            | Gold          | CryptoCurrency |
      | 1kbr8vn       | -0.6               | ETH            | gas           | ethereum       |
      | 1j5m2pq       | 0.6                | SOL            | wallet        | solana         |