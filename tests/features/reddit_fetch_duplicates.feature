# tests/features/reddit_fetch_duplicates.feature
Feature: Handling Duplicate Reddit Posts

  Scenario: Fetching Reddit posts containing duplicates
    Given the Reddit API returns posts with duplicate IDs
    And the test database is set up
    When the Reddit posts are fetched and stored
    Then the database contains only unique posts