from typing import Dict, List

import pytest
from pydantic import BaseModel
from pytest_bdd import given, parsers, scenarios, then, when

# Import the functions to test
from reddit_fetch import extract_mentioned_coins

# Register scenarios from the coin extraction feature file
scenarios('../coin_extraction.feature')


class ExtractionData(BaseModel):
    title: str
    content: str
    coin_keywords: Dict[str, List[str]]
    mentioned_coins: List[str]


@pytest.fixture
def test_coin_keywords() -> Dict[str, List[str]]:
    """Provide a smaller set of coin keywords for testing."""
    return {
        'BTC': ['BTC', 'BITCOIN', 'BTCUSD'],
        'ETH': ['ETH', 'ETHEREUM', 'ETHUSD'],
        'ADA': ['ADA', 'CARDANO', 'HOSKINSON'],
        'SOL': ['SOL', 'SOLANA']
    }


@given("a set of cryptocurrency keywords", target_fixture="coin_keywords")
def given_cryptocurrency_keywords(test_coin_keywords: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Return coin keywords for use in steps."""
    return test_coin_keywords


@when(parsers.parse('I analyze the title "{title}" and content "{content}"'), target_fixture="extraction_data")
def analyze_text(title: str, content: str, coin_keywords: Dict[str, List[str]]) -> ExtractionData:
    """Analyze text for coin mentions and store input for later assertions."""
    return ExtractionData(title=title,
                          content=content,
                          coin_keywords=coin_keywords,
                          mentioned_coins=extract_mentioned_coins(title, content, coin_keywords))


@then(parsers.parse('the extracted coins should include "{coin}"'))
def extracted_coins_include(extraction_data: ExtractionData, coin: str) -> None:
    """Check if extracted coins include the expected coin."""
    assert coin in extraction_data.mentioned_coins


@then(parsers.parse('the extracted coins should not include "{coin}"'))
def extracted_coins_not_include(extraction_data: ExtractionData, coin: str) -> None:
    """Check if extracted coins don't include the specified coin."""
    assert coin not in extraction_data.mentioned_coins if extraction_data.mentioned_coins else True


@then("there should be no extracted coins")
def no_extracted_coins(extraction_data: ExtractionData) -> None:
    """Check if no coins were extracted."""
    assert len(extraction_data.mentioned_coins) == 0
