Feature: Sentiment Analysis
  As a crypto sentiment analyzer
  I want to determine the sentiment of text
  So that I can understand market sentiment for cryptocurrencies

  Scenario Outline: Determine sentiment from score
    When I have a sentiment score of <score>
    Then the sentiment should be classified as "<sentiment>"

    Examples:
      | score |  sentiment |
      |  0.5  |  Positive  |
      |  0.05 |  Positive  |
      |  0.0  |  Neutral   |
      | -0.05 |  Negative  |
      | -0.5  |  Negative  | 