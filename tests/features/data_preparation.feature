Feature: Data Preparation
  As a crypto sentiment analyst
  I want to prepare sentiment data from the database
  So that I can analyze and visualize it correctly

  Scenario: Successfully preparing sentiment data
    Given the database contains sentiment data
    When I prepare the data
    Then the result should be a DataFrame
    And the DataFrame should have a 'published_at' column with datetime values
    And the DataFrame should have a 'sentiment_category' column
    And the sentiment categories should be correctly assigned