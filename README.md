# Cryptocurrency Sentiment Analysis for Reddit

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=mico_crypto_sentiment_analysis&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=mico_crypto_sentiment_analysis)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=mico_crypto_sentiment_analysis&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=mico_crypto_sentiment_analysis)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=mico_crypto_sentiment_analysis&metric=coverage)](https://sonarcloud.io/dashboard?id=mico_crypto_sentiment_analysis)

A comprehensive tool for collecting, analyzing, and visualizing cryptocurrency sentiment data from Reddit.

## Overview

Aggregates and analyzes sentiment data related to cryptocurrencies from Reddit

The collected data is analyzed for sentiment (positive, neutral, negative) using natural language processing techniques and stored in a SQLite database. A Streamlit dashboard provides visualizations and insights from the collected data.

## Features

- Automatic sentiment analysis using VADER and TextBlob
- Entity recognition for major cryptocurrencies (BTC, ETH, SOL, etc.)
- Persistent storage with SQLite database
- Interactive dashboard with Streamlit
- Time series analysis of sentiment trends
- Cryptocurrency popularity metrics

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mico/crypto_sentiment_analysis.git
cd crypto_sentiment_analysis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Reddit API credentials
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USER_AGENT="your_user_agent"

## Usage

### Data Collection

1. Collect Reddit data:
```bash
python reddit_fetch.py
```

### Dashboard

Launch the Streamlit dashboard:
```bash
streamlit run app.py
```

The dashboard will be accessible at `http://localhost:8501` and displays:
- Sentiment distribution charts
- Cryptocurrency mentions by frequency
- Sentiment trends over time
- Individual articles sorted by sentiment
- Crypto-specific sentiment analysis

## Project Structure

- `reddit_fetch.py`: Fetches and analyzes Reddit posts
- `app.py`: Streamlit dashboard application
- `crypto_data.db`: SQLite database storing all sentiment data
- `requirements.txt`: Project dependencies

## Dependencies

- praw: Reddit API wrapper
- pandas: Data manipulation
- textblob: Text processing and sentiment analysis
- vaderSentiment: Sentiment analysis
- streamlit: Dashboard visualization
- plotly: Interactive charts
- sqlite3: Database management
- requests: API calls

## Future Improvements

- MCP support
- REST API

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 