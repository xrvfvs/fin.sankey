# -*- coding: utf-8 -*-
"""
Financial news feed module using yfinance.
"""

import streamlit as st
import yfinance as yf
from datetime import datetime
from typing import List, Dict, Optional

from modules.logger import log_error, log_warning, log_api_call
from modules.i18n import t


@st.cache_data(ttl=1800)  # Cache for 30 minutes
def fetch_news(ticker_symbol: str, max_items: int = 10) -> List[Dict]:
    """
    Fetch news articles for a given ticker.

    Args:
        ticker_symbol: Stock ticker symbol
        max_items: Maximum number of news items to return

    Returns:
        List of news article dictionaries
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news

        if not news:
            log_warning(f"No news found for {ticker_symbol}")
            return []

        articles = []
        for item in news[:max_items]:
            article = {
                'title': item.get('title', 'No title'),
                'publisher': item.get('publisher', 'Unknown'),
                'link': item.get('link', '#'),
                'published': _format_timestamp(item.get('providerPublishTime')),
                'type': item.get('type', 'article'),
                'thumbnail': _get_thumbnail(item),
                'related_tickers': item.get('relatedTickers', [])
            }
            articles.append(article)

        log_api_call("yfinance_news", ticker=ticker_symbol, success=True)
        return articles

    except Exception as e:
        log_error(e, f"Error fetching news for {ticker_symbol}")
        log_api_call("yfinance_news", ticker=ticker_symbol, success=False)
        return []


def _format_timestamp(timestamp: Optional[int]) -> str:
    """Format Unix timestamp to readable string."""
    if not timestamp:
        return "Unknown date"
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "Unknown date"


def _get_thumbnail(item: Dict) -> Optional[str]:
    """Extract thumbnail URL from news item."""
    try:
        if 'thumbnail' in item and item['thumbnail']:
            resolutions = item['thumbnail'].get('resolutions', [])
            if resolutions:
                # Get medium-sized thumbnail
                for res in resolutions:
                    if res.get('width', 0) >= 100:
                        return res.get('url')
                # Fallback to first available
                return resolutions[0].get('url')
    except Exception:
        pass
    return None


def render_news_feed(ticker_symbol: str, show_thumbnails: bool = True):
    """
    Render news feed in Streamlit UI.

    Args:
        ticker_symbol: Stock ticker symbol
        show_thumbnails: Whether to show article thumbnails
    """
    news = fetch_news(ticker_symbol)

    if not news:
        st.info(t('no_news_available', ticker=ticker_symbol))
        return

    st.subheader(f"📰 {t('news_title', ticker=ticker_symbol)}")

    for article in news:
        with st.container():
            cols = st.columns([1, 4] if show_thumbnails and article['thumbnail'] else [1])

            if show_thumbnails and article['thumbnail']:
                with cols[0]:
                    st.image(article['thumbnail'], width=100)
                content_col = cols[1]
            else:
                content_col = cols[0] if len(cols) == 1 else cols[1]

            with content_col:
                # Title with link
                st.markdown(f"**[{article['title']}]({article['link']})**")

                # Meta info
                meta = f"📅 {article['published']} | 📰 {article['publisher']}"
                st.caption(meta)

                # Related tickers
                if article['related_tickers']:
                    related = ", ".join(article['related_tickers'][:5])
                    st.caption(f"🏷️ {related}")

            st.markdown("---")


def render_news_sidebar(ticker_symbol: str, max_items: int = 5):
    """
    Render compact news feed in sidebar.

    Args:
        ticker_symbol: Stock ticker symbol
        max_items: Maximum number of items to show
    """
    news = fetch_news(ticker_symbol, max_items=max_items)

    if not news:
        return

    st.sidebar.markdown(f"### 📰 {t('latest_news')}")

    for article in news:
        st.sidebar.markdown(f"• [{article['title'][:50]}...]({article['link']})")
        st.sidebar.caption(f"{article['publisher']} - {article['published']}")


def get_market_sentiment_from_news(ticker_symbol: str) -> Dict:
    """
    Analyze news headlines for basic sentiment indicators.

    Args:
        ticker_symbol: Stock ticker symbol

    Returns:
        Dictionary with sentiment indicators
    """
    news = fetch_news(ticker_symbol, max_items=20)

    if not news:
        return {'status': 'no_data', 'news_count': 0}

    # Simple keyword-based sentiment (basic implementation)
    positive_keywords = ['surge', 'jump', 'gain', 'rise', 'beat', 'profit', 'growth', 'upgrade', 'buy', 'bullish']
    negative_keywords = ['fall', 'drop', 'loss', 'miss', 'decline', 'downgrade', 'sell', 'bearish', 'cut', 'warning']

    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for article in news:
        title_lower = article['title'].lower()
        has_positive = any(kw in title_lower for kw in positive_keywords)
        has_negative = any(kw in title_lower for kw in negative_keywords)

        if has_positive and not has_negative:
            positive_count += 1
        elif has_negative and not has_positive:
            negative_count += 1
        else:
            neutral_count += 1

    total = len(news)
    return {
        'status': 'ok',
        'news_count': total,
        'positive': positive_count,
        'negative': negative_count,
        'neutral': neutral_count,
        'positive_ratio': positive_count / total if total > 0 else 0,
        'negative_ratio': negative_count / total if total > 0 else 0,
        'sentiment_score': (positive_count - negative_count) / total if total > 0 else 0
    }
