Feature: Reddit Data Fetching and Integration
  As a data analyst
  I want to fetch cryptocurrency-related data from Reddit
  So that I can analyze sentiment and trends

  Scenario: Complete workflow from fetching to storage
    Given a Configuration file for test
    And the test database is set up
    When I run the complete data fetch workflow
    Then I should be able to retrieve the posts from the database
