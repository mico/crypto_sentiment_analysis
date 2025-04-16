Feature: Cryptocurrency Mention Extraction
  As a crypto sentiment analyzer
  I want to extract cryptocurrency mentions from text
  So that I can track which cryptocurrencies are being discussed

  Background:
    Given a set of cryptocurrency keywords

  Scenario: Extract Bitcoin mentions
    When I analyze the title "Bitcoin is going up" and content "BTC to the moon!"
    Then the extracted coins should include "BTC"

  Scenario: Extract multiple coin mentions
    When I analyze the title "ETH vs BTC" and content "Ethereum and Bitcoin comparison"
    Then the extracted coins should include "BTC"
    And the extracted coins should include "ETH"

  Scenario: No coin mentions
    When I analyze the title "Market analysis" and content "The crypto market is volatile"
    Then there should be no extracted coins

  Scenario: Whole word matching for coin mentions
    When I analyze the title "The ADAPTATION of blockchain technology" and content "Blockchain solutions are evolving"
    Then the extracted coins should not include "ADA"

  Scenario: Proper word boundaries with punctuation
    When I analyze the title "SOL: A fast blockchain. SOLANA is growing!" and content "Investing in SOL."
    Then the extracted coins should include "SOL" 