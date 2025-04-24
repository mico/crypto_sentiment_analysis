from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Union

import pandas as pd
import plotly.express as px  # type: ignore [import-untyped]
import pytz
from sqlalchemy import Engine
import streamlit as st

from database import get_engine

# Define sentiment thresholds for classification
POSITIVE_THRESHOLD = 0.3
NEGATIVE_THRESHOLD = -0.3


def prepare_data(engine: Engine) -> pd.DataFrame:
    query = "SELECT * FROM sentiment_data"
    query_df: pd.DataFrame = pd.read_sql_query(query, engine)

    # Update the datetime parsing to handle mixed formats
    query_df['published_at'] = pd.to_datetime(
        query_df['published_at'], format='mixed', utc=True
    ).dt.tz_localize(None)

    # Convert sentiment to float
    # now database store sentiment as text, we need to convert it to float
    query_df['sentiment'] = query_df['sentiment'].astype(float)

    # Create a sentiment category column based on float sentiment values
    query_df['sentiment_category'] = pd.cut(
        query_df['sentiment'],
        bins=[-float('inf'), NEGATIVE_THRESHOLD, POSITIVE_THRESHOLD, float('inf')],
        labels=["Negative", "Neutral", "Positive"]
    )
    return query_df


def render_app(query_df: pd.DataFrame) -> None:
    st.set_page_config(
        page_title="Reddit sentiment data",
        page_icon="chart_with_upwards_trend",
        layout="wide"
    )

    st.header("Reddit sentiment data")

    # Add data source selector
    data_source = st.selectbox(
        "Select Data Source",
        options=["All Sources", "CryptoPanic", "Reddit"],
        index=0  # Default to "All Sources"
    )

    # Filter data based on selected source
    if data_source == "CryptoPanic":
        # Consider both explicit cryptopanic.com domain and NULL/empty domains as CryptoPanic data
        query_df = query_df[
            (query_df['domain'] == 'cryptopanic.com') |
            (query_df['domain'].isna()) |
            (query_df['domain'] == '')
        ]
    elif data_source == "Reddit":
        query_df = query_df[query_df['domain'] == 'reddit.com']
    # If "All Sources" is selected, we keep all data

    china_tz = pytz.timezone('Asia/Shanghai')
    current_time_china = datetime.now(pytz.utc).astimezone(china_tz).replace(microsecond=0)
    latest_article_time = pd.to_datetime(
        query_df['published_at'].max()
    ).tz_localize(pytz.UTC).astimezone(china_tz)

    st.subheader("Dates")
    st.write(f"- Dashboard last refreshed: {current_time_china}")
    st.write(f"- Latest article available: {latest_article_time}")
    if data_source != "All Sources":
        st.write(f"- Showing data from: {data_source}")

    st.subheader("Select Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Select a start date",
            min_value=query_df['published_at'].min(),
            max_value=query_df['published_at'].max(),
            value=query_df['published_at'].max()
        )
    with col2:
        end_date = st.date_input(
            "Select a end date",
            min_value=start_date,
            max_value=query_df['published_at'].max(),
            value=query_df['published_at'].max()
        )

    filtered_df = query_df[
        (query_df['published_at'].dt.date >= start_date) &
        (query_df['published_at'].dt.date <= end_date)
    ]
    filtered_df['datetime'] = filtered_df['published_at'].dt.floor('h')
    filtered_df['date'] = filtered_df['published_at'].dt.floor('D')

    col1, col2 = st.columns(2)
    with col1:
        counts_df = filtered_df.groupby(['sentiment_category']).agg({'id': 'count'}).reset_index()
        filtered_agg_df = filtered_df.groupby(
            ['datetime', 'sentiment_category']
        ).agg({'id': 'count'}).reset_index()
        crypto_list: List[str] = sum(
            [x.split(',') for x in filtered_df['coins'].values if x != ''],
            []
        )
        crypto_list = [x for x in crypto_list if x not in ['OG', 'U']]
        crypto_count_dict = Counter(crypto_list)
        crypto_count_df = pd.DataFrame(
            list(crypto_count_dict.items()),
            columns=['crypto', 'count']
        ).sort_values('count', ascending=False)
        st.subheader("Cryptos by Mention")
        st.write(
            f"Top 5 cryptos by mention: "
            f"{', '.join([str(x[0]) for x in crypto_count_df.head(5).values])}"
        )
        fig = px.pie(crypto_count_df, names="crypto", values='count')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig)
    with col2:
        st.subheader('Top 10 Cryptos by Sentiment Counts')
        crypto_list_unique = list(set(crypto_list))
        crypto_list_unique.sort()
        crypto_dict_list: List[Dict[str, Union[str, int, float]]] = []
        for crypto in crypto_list_unique:
            crypto_dict: Dict[str, Union[str, int, float]] = {}
            crypto_dict['coins'] = crypto
            crypto_df = filtered_df[filtered_df['coins'].str.contains(crypto)]
            crypto_dict['positive_count'] = len(
                crypto_df[crypto_df['sentiment_category'] == "Positive"]
            )
            crypto_dict['neutral_count'] = len(
                crypto_df[crypto_df['sentiment_category'] == "Neutral"]
            )
            crypto_dict['negative_count'] = len(
                crypto_df[crypto_df['sentiment_category'] == "Negative"]
            )
            crypto_dict['total'] = len(crypto_df)
            crypto_dict_list.append(crypto_dict)
        crypto_sentiment_df = pd.DataFrame(crypto_dict_list).sort_values('total', ascending=False)

        # Fix line length issues
        top_pos = crypto_sentiment_df.sort_values('positive_count', ascending=False).head(5)
        top_pos_str = ', '.join([str(x[0]) for x in top_pos.values])
        st.write(f"Top 5 cryptos by positive counts: {top_pos_str}")

        top_neg = crypto_sentiment_df.sort_values('negative_count', ascending=False).head(5)
        top_neg_str = ', '.join([str(x[0]) for x in top_neg.values])
        st.write(f"Top 5 cryptos by negative counts: {top_neg_str}")

        st.plotly_chart(px.bar(
            crypto_sentiment_df.head(10),
            x="coins",
            y=["positive_count", "neutral_count", "negative_count"]
        ))

    col1, col2, col3 = st.columns(3)
    for idx, sentiment in enumerate(["Positive", "Neutral", "Negative"], 1):
        ts_df = filtered_agg_df[filtered_agg_df['sentiment_category'] == sentiment]
        max_time = ts_df['datetime'].max()
        max_time_24h_before = max_time - timedelta(hours=24)
        ts_24h_df = ts_df[
            (ts_df['datetime'] <= max_time) &
            (ts_df['datetime'] >= max_time_24h_before)
        ]

        # Check if we have valid datetime values before creating date_range
        if not pd.isna(ts_24h_df['datetime'].min()) and not pd.isna(ts_24h_df['datetime'].max()):
            date_range = pd.date_range(
                ts_24h_df['datetime'].min(),
                ts_24h_df['datetime'].max(),
                freq='h'
            )
            dates_df = pd.DataFrame(columns=['datetime'], data=date_range)
            dates_df = dates_df.merge(
                ts_24h_df[['datetime', 'id']], how='left', on='datetime'
            ).fillna(0)[['datetime', 'id']]
        else:
            # Create empty DataFrame with columns if no valid data
            dates_df = pd.DataFrame(columns=['datetime', 'id'])

        # Get count for this sentiment safely
        sentiment_count = 0
        sentiment_rows = counts_df[counts_df['sentiment_category'] == sentiment]
        if not sentiment_rows.empty:
            sentiment_count = sentiment_rows['id'].values[0]

        if idx == 1:
            with col1:
                st.subheader(f"{sentiment} Sentiment Articles")
                st.metric("Article count:", sentiment_count)
                st.plotly_chart(px.area(
                    dates_df,
                    x="datetime",
                    y="id",
                    title='Articles in the Last 24h:',
                    color_discrete_sequence=["limegreen"],
                    width=550,
                    height=500
                ))
        if idx == 2:
            with col2:
                st.subheader(f"{sentiment} Sentiment Articles")
                st.metric("Article count:", sentiment_count)
                st.plotly_chart(px.area(
                    dates_df,
                    x="datetime",
                    y="id",
                    title='Articles in the Last 24h:',
                    color_discrete_sequence=["gray"],
                    width=550,
                    height=500
                ))
        if idx == 3:
            with col3:
                st.subheader(f"{sentiment} Sentiment Articles")
                st.metric("Article count:", sentiment_count)
                st.plotly_chart(px.area(
                    dates_df,
                    x="datetime",
                    y="id",
                    title='Articles in the Last 24h:',
                    color_discrete_sequence=["red"],
                    width=550,
                    height=500
                ))

    coin_selection = st.selectbox("Select a crypto", options=crypto_list_unique)

    filtered_df = filtered_df[filtered_df['coins'].str.contains(coin_selection)]

    pos_filtered_df = filtered_df[filtered_df['sentiment_category'] == "Positive"].sort_values(
        'datetime', ascending=False
    )
    neu_filtered_df = filtered_df[filtered_df['sentiment_category'] == "Neutral"].sort_values(
        'datetime', ascending=False
    )
    neg_filtered_df = filtered_df[filtered_df['sentiment_category'] == "Negative"].sort_values(
        'datetime', ascending=False
    )

    pos_rate = len(pos_filtered_df)
    neu_rate = len(neu_filtered_df)
    neg_rate = len(neg_filtered_df)

    metric1, metric2, metric3 = st.columns(3)

    def display_articles(
        filtered_df: pd.DataFrame,
        label: str,
        value: int
    ) -> None:
        st.metric(label=label, value=value)
        if value > 0:
            st.write("Articles:")
        dates = set(filtered_df['date'].values)
        for date in dates:
            st.markdown(f'- {pd.to_datetime(date).date()}')
            # Get articles for this date
            articles_for_date = filtered_df[filtered_df['date'] == date]
            for _, article in articles_for_date.iterrows():
                # Determine URL based on domain
                domain = article['domain']
                if domain is None or domain == '' or 'cryptopanic' in str(domain):
                    url = f'https://cryptopanic.com/news/click/{article["id"]}/'
                else:
                    url = article['url']
                # Display article title with link
                st.markdown(f"[{article['title']}]({url})")

    with metric1:
        display_articles(pos_filtered_df, "Positive Articles", pos_rate)

    with metric2:
        display_articles(neu_filtered_df, "Neutral Articles", neu_rate)

    with metric3:
        display_articles(neg_filtered_df, "Negative Articles", neg_rate)


if __name__ == "__main__":
    render_app(prepare_data(get_engine()))
