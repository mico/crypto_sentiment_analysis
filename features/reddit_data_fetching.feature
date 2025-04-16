Feature: Reddit Data Fetching
  As a crypto sentiment analyzer
  I want to fetch cryptocurrency-related data from Reddit
  So that I can analyze sentiment about specific cryptocurrencies

  Background:
    Given a Reddit client
    And a sentiment analyzer
    And a set of cryptocurrency keywords

  @vcr
  Scenario: Fetch Bitcoin-related data from Reddit
    When I fetch data from the "Bitcoin" subreddit
    Then I should get a list of post data
    And each post should mention "BTC"
    And each post should contain the required fields
    And each post should have a sentiment classification

  @vcr
  Scenario: Fetch general cryptocurrency data from Reddit
    When I fetch data from the "CryptoCurrency" subreddit
    Then I should get a list of post data
    And the results should include mentions of at least one test coin 