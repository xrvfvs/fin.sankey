# -*- coding: utf-8 -*-
"""
Portfolio tracker and technical analysis module.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from modules.logger import log_error, log_warning, log_api_call
from modules.utils import retry_on_rate_limit, get_yf_ticker
from modules.i18n import t


# --- TECHNICAL ANALYSIS FUNCTIONS ---

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        prices: Series of closing prices
        period: RSI period (default 14)

    Returns:
        Series with RSI values
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        prices: Series of closing prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)

    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()

    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Args:
        prices: Series of closing prices
        period: Moving average period (default 20)
        std_dev: Number of standard deviations (default 2)

    Returns:
        Tuple of (Upper band, Middle band, Lower band)
    """
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return upper, middle, lower


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()


@st.cache_data(ttl=300)  # Cache for 5 minutes
@retry_on_rate_limit(max_retries=5, base_delay=3)
def get_technical_signals(ticker_symbol: str, period: str = "6mo") -> Dict:
    """
    Get technical analysis signals for a stock.

    Args:
        ticker_symbol: Stock ticker symbol
        period: Data period (default 6 months)

    Returns:
        Dictionary with technical indicators and signals
    """
    try:
        ticker = get_yf_ticker(ticker_symbol)
        hist = ticker.history(period=period)

        if hist.empty or len(hist) < 30:
            return {'status': 'insufficient_data'}

        close = hist['Close']

        # Calculate indicators
        rsi = calculate_rsi(close)
        macd_line, signal_line, macd_hist = calculate_macd(close)
        upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(close)
        sma_20 = calculate_sma(close, 20)
        sma_50 = calculate_sma(close, 50)
        sma_200 = calculate_sma(close, 200) if len(close) >= 200 else None

        # Get latest values
        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_macd_hist = macd_hist.iloc[-1]

        # Generate signals
        signals = []

        # RSI signals
        if current_rsi < 30:
            signals.append(('RSI', 'oversold', 'bullish'))
        elif current_rsi > 70:
            signals.append(('RSI', 'overbought', 'bearish'))
        else:
            signals.append(('RSI', 'neutral', 'neutral'))

        # MACD signals
        if current_macd > current_signal:
            signals.append(('MACD', 'above_signal', 'bullish'))
        else:
            signals.append(('MACD', 'below_signal', 'bearish'))

        # Bollinger Bands signals
        if current_price > upper_bb.iloc[-1]:
            signals.append(('BB', 'above_upper', 'bearish'))
        elif current_price < lower_bb.iloc[-1]:
            signals.append(('BB', 'below_lower', 'bullish'))
        else:
            signals.append(('BB', 'within_bands', 'neutral'))

        # Moving Average signals
        if sma_200 is not None and not pd.isna(sma_200.iloc[-1]):
            if current_price > sma_200.iloc[-1]:
                signals.append(('SMA200', 'above', 'bullish'))
            else:
                signals.append(('SMA200', 'below', 'bearish'))

        # Overall signal
        bullish_count = sum(1 for _, _, sig in signals if sig == 'bullish')
        bearish_count = sum(1 for _, _, sig in signals if sig == 'bearish')

        if bullish_count > bearish_count + 1:
            overall = 'bullish'
        elif bearish_count > bullish_count + 1:
            overall = 'bearish'
        else:
            overall = 'neutral'

        log_api_call("technical_analysis", ticker=ticker_symbol, success=True)

        return {
            'status': 'ok',
            'ticker': ticker_symbol,
            'price': current_price,
            'rsi': current_rsi,
            'macd': current_macd,
            'macd_signal': current_signal,
            'macd_histogram': current_macd_hist,
            'sma_20': sma_20.iloc[-1],
            'sma_50': sma_50.iloc[-1],
            'sma_200': sma_200.iloc[-1] if sma_200 is not None else None,
            'bb_upper': upper_bb.iloc[-1],
            'bb_middle': middle_bb.iloc[-1],
            'bb_lower': lower_bb.iloc[-1],
            'signals': signals,
            'overall_signal': overall,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count
        }

    except Exception as e:
        log_error(e, f"Error calculating technical indicators for {ticker_symbol}")
        return {'status': 'error', 'message': str(e)}


# --- PORTFOLIO FUNCTIONS ---

@st.cache_data(ttl=300)  # Cache for 5 minutes
@retry_on_rate_limit(max_retries=5, base_delay=3)
def get_stock_price(ticker_symbol: str) -> Dict:
    """
    Get current stock price and daily change.

    Args:
        ticker_symbol: Stock ticker symbol

    Returns:
        Dictionary with price data
    """
    try:
        ticker = get_yf_ticker(ticker_symbol)
        info = ticker.info

        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        previous_close = info.get('previousClose', 0)

        if previous_close > 0:
            change = current_price - previous_close
            change_pct = (change / previous_close) * 100
        else:
            change = 0
            change_pct = 0

        return {
            'price': current_price,
            'previous_close': previous_close,
            'change': change,
            'change_pct': change_pct,
            'name': info.get('shortName', ticker_symbol),
            'currency': info.get('currency', 'USD')
        }

    except Exception as e:
        log_warning(f"Failed to get price for {ticker_symbol}: {e}")
        return {'price': 0, 'change': 0, 'change_pct': 0, 'name': ticker_symbol}


def calculate_portfolio_value(holdings: List[Dict]) -> Dict:
    """
    Calculate total portfolio value and performance.

    Args:
        holdings: List of holdings with ticker, shares, avg_cost

    Returns:
        Dictionary with portfolio metrics
    """
    if not holdings:
        return {
            'total_value': 0,
            'total_cost': 0,
            'total_gain': 0,
            'total_gain_pct': 0,
            'daily_change': 0,
            'holdings': []
        }

    total_value = 0
    total_cost = 0
    daily_change = 0
    enriched_holdings = []

    for holding in holdings:
        ticker = holding.get('ticker', '')
        shares = holding.get('shares', 0)
        avg_cost = holding.get('avg_cost', 0)

        price_data = get_stock_price(ticker)
        current_price = price_data.get('price', 0)

        position_value = shares * current_price
        position_cost = shares * avg_cost
        position_gain = position_value - position_cost
        position_gain_pct = (position_gain / position_cost * 100) if position_cost > 0 else 0

        daily_position_change = shares * price_data.get('change', 0)

        total_value += position_value
        total_cost += position_cost
        daily_change += daily_position_change

        enriched_holdings.append({
            **holding,
            'current_price': current_price,
            'position_value': position_value,
            'position_cost': position_cost,
            'gain': position_gain,
            'gain_pct': position_gain_pct,
            'daily_change': daily_position_change,
            'daily_change_pct': price_data.get('change_pct', 0),
            'name': price_data.get('name', ticker)
        })

    total_gain = total_value - total_cost
    total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_gain': total_gain,
        'total_gain_pct': total_gain_pct,
        'daily_change': daily_change,
        'daily_change_pct': (daily_change / (total_value - daily_change) * 100) if total_value > daily_change else 0,
        'holdings': enriched_holdings
    }


def render_technical_indicators(ticker_symbol: str):
    """
    Render technical analysis section in Streamlit.

    Args:
        ticker_symbol: Stock ticker symbol
    """
    st.subheader(f"{t('technical_analysis')} - {ticker_symbol}")

    with st.spinner(t('loading_indicators')):
        signals = get_technical_signals(ticker_symbol)

    if signals.get('status') != 'ok':
        st.warning(t('insufficient_data_for_analysis'))
        return

    # Display current price and overall signal
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            t('current_price'),
            f"${signals['price']:.2f}"
        )

    with col2:
        overall = signals['overall_signal']
        signal_display = {
            'bullish': ('↑', 'Bullish'),
            'bearish': ('↓', 'Bearish'),
            'neutral': ('→', 'Neutral')
        }
        arrow, label = signal_display.get(overall, ('?', overall.upper()))
        st.metric(
            t('overall_signal'),
            f"{arrow} {label}"
        )

    with col3:
        st.metric(
            "RSI (14)",
            f"{signals['rsi']:.1f}",
            delta="Oversold" if signals['rsi'] < 30 else "Overbought" if signals['rsi'] > 70 else "Neutral"
        )

    # Detailed indicators
    st.markdown("---")

    ind_col1, ind_col2, ind_col3, ind_col4 = st.columns(4)

    with ind_col1:
        st.markdown("**MACD**")
        macd_status = "↑ Bullish" if signals['macd'] > signals['macd_signal'] else "↓ Bearish"
        st.write(f"MACD: {signals['macd']:.4f}")
        st.write(f"Signal: {signals['macd_signal']:.4f}")
        st.write(f"Status: {macd_status}")

    with ind_col2:
        st.markdown("**Bollinger Bands**")
        st.write(f"Upper: ${signals['bb_upper']:.2f}")
        st.write(f"Middle: ${signals['bb_middle']:.2f}")
        st.write(f"Lower: ${signals['bb_lower']:.2f}")

    with ind_col3:
        st.markdown("**Moving Averages**")
        st.write(f"SMA 20: ${signals['sma_20']:.2f}")
        st.write(f"SMA 50: ${signals['sma_50']:.2f}")
        if signals['sma_200']:
            st.write(f"SMA 200: ${signals['sma_200']:.2f}")

    with ind_col4:
        st.markdown("**Signals Summary**")
        st.write(f"↑ Bullish: {signals['bullish_count']}")
        st.write(f"↓ Bearish: {signals['bearish_count']}")
        st.write(f"Overall: {signals['overall_signal'].upper()}")


def render_portfolio_summary(holdings: List[Dict]):
    """
    Render portfolio summary in Streamlit.

    Args:
        holdings: List of portfolio holdings
    """
    if not holdings:
        st.info(t('portfolio_empty'))
        return

    portfolio = calculate_portfolio_value(holdings)

    # Portfolio header metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            t('total_value'),
            f"${portfolio['total_value']:,.2f}"
        )

    with col2:
        gain_color = "normal" if portfolio['total_gain'] >= 0 else "inverse"
        st.metric(
            t('total_gain'),
            f"${portfolio['total_gain']:,.2f}",
            delta=f"{portfolio['total_gain_pct']:.2f}%"
        )

    with col3:
        st.metric(
            t('daily_change'),
            f"${portfolio['daily_change']:,.2f}",
            delta=f"{portfolio['daily_change_pct']:.2f}%"
        )

    with col4:
        st.metric(
            t('positions'),
            len(portfolio['holdings'])
        )

    # Holdings table
    st.markdown("---")
    st.subheader(t('holdings'))

    for holding in portfolio['holdings']:
        with st.container():
            cols = st.columns([2, 1, 1, 1, 1, 1])

            with cols[0]:
                st.markdown(f"**{holding['ticker']}**")
                st.caption(holding.get('name', ''))

            with cols[1]:
                st.write(f"{holding['shares']} shares")
                st.caption(f"Avg: ${holding['avg_cost']:.2f}")

            with cols[2]:
                st.write(f"${holding['current_price']:.2f}")
                change_symbol = "↑" if holding['daily_change_pct'] >= 0 else "↓"
                st.caption(f"{change_symbol} {holding['daily_change_pct']:+.2f}%")

            with cols[3]:
                st.write(f"${holding['position_value']:,.2f}")

            with cols[4]:
                gain_symbol = "+" if holding['gain'] >= 0 else ""
                st.write(f"{gain_symbol}${holding['gain']:,.2f}")
                st.caption(f"{holding['gain_pct']:+.2f}%")

            with cols[5]:
                # Technical signal for this holding
                signals = get_technical_signals(holding['ticker'])
                if signals.get('status') == 'ok':
                    signal_display = {'bullish': '↑ Buy', 'bearish': '↓ Sell', 'neutral': '→ Hold'}
                    overall = signals['overall_signal']
                    st.write(signal_display.get(overall, '?'))
                    st.caption(f"RSI: {signals['rsi']:.0f}")

            st.markdown("---")
