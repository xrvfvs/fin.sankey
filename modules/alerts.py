# -*- coding: utf-8 -*-
"""
Price alerts module for monitoring stock price changes.
"""

import streamlit as st
import yfinance as yf
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

from modules.logger import log_error, log_warning, log_info, log_user_action
from modules.utils import retry_on_rate_limit, get_yf_ticker, yf_throttle
from modules.i18n import t


class AlertType(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE_UP = "percent_up"
    PERCENT_CHANGE_DOWN = "percent_down"


ALERT_TYPE_LABELS = {
    AlertType.PRICE_ABOVE: ("Price Above", "Cena Powyżej"),
    AlertType.PRICE_BELOW: ("Price Below", "Cena Poniżej"),
    AlertType.PERCENT_CHANGE_UP: ("% Change Up", "Wzrost %"),
    AlertType.PERCENT_CHANGE_DOWN: ("% Change Down", "Spadek %"),
}


@st.cache_data(ttl=60)  # Cache for 1 minute
@retry_on_rate_limit(max_retries=5, base_delay=3)
def get_current_price(ticker_symbol: str) -> Optional[float]:
    """
    Get current stock price.

    Args:
        ticker_symbol: Stock ticker symbol

    Returns:
        Current price or None if failed
    """
    try:
        ticker = get_yf_ticker(ticker_symbol)
        yf_throttle()
        info = ticker.info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        return float(price) if price else None
    except Exception as e:
        log_warning(f"Failed to get price for {ticker_symbol}: {e}")
        return None


def check_alert_triggered(alert: Dict, current_price: float) -> bool:
    """
    Check if an alert condition is met.

    Args:
        alert: Alert dictionary with type, target_value, etc.
        current_price: Current stock price

    Returns:
        True if alert is triggered
    """
    alert_type = alert.get('alert_type')
    target = alert.get('target_value', 0)
    base_price = alert.get('base_price', current_price)

    if alert_type == AlertType.PRICE_ABOVE.value:
        return current_price >= target

    elif alert_type == AlertType.PRICE_BELOW.value:
        return current_price <= target

    elif alert_type == AlertType.PERCENT_CHANGE_UP.value:
        if base_price > 0:
            change_pct = ((current_price - base_price) / base_price) * 100
            return change_pct >= target
        return False

    elif alert_type == AlertType.PERCENT_CHANGE_DOWN.value:
        if base_price > 0:
            change_pct = ((base_price - current_price) / base_price) * 100
            return change_pct >= target
        return False

    return False


def check_user_alerts(alerts: List[Dict]) -> List[Dict]:
    """
    Check all user alerts and return triggered ones.

    Args:
        alerts: List of alert dictionaries

    Returns:
        List of triggered alerts with current prices
    """
    triggered = []

    for alert in alerts:
        if alert.get('is_active', True):
            ticker = alert.get('ticker')
            current_price = get_current_price(ticker)

            if current_price is not None:
                if check_alert_triggered(alert, current_price):
                    triggered.append({
                        **alert,
                        'current_price': current_price,
                        'triggered_at': datetime.now().isoformat()
                    })

    return triggered


def render_alert_form(tickers_list: List[str] = None):
    """
    Render form to create a new price alert.

    Args:
        tickers_list: Optional list of tickers for dropdown

    Returns:
        Dict with alert data if form submitted, None otherwise
    """
    st.subheader(f"➕ {t('create_alert')}")

    col1, col2 = st.columns(2)

    with col1:
        ticker = st.text_input(
            t('ticker'),
            placeholder="AAPL",
            key="alert_ticker"
        ).upper()

        alert_type = st.selectbox(
            t('alert_type'),
            options=[at.value for at in AlertType],
            format_func=lambda x: ALERT_TYPE_LABELS.get(AlertType(x), (x, x))[0],
            key="alert_type"
        )

    with col2:
        if alert_type in [AlertType.PRICE_ABOVE.value, AlertType.PRICE_BELOW.value]:
            target_value = st.number_input(
                t('target_price'),
                min_value=0.01,
                value=100.0,
                step=0.01,
                key="alert_target"
            )
            # Get current price for reference
            if ticker:
                current = get_current_price(ticker)
                if current:
                    st.caption(f"📊 {t('current_price')}: ${current:.2f}")
        else:
            target_value = st.number_input(
                t('target_percent'),
                min_value=0.1,
                max_value=100.0,
                value=5.0,
                step=0.1,
                key="alert_target_pct"
            )
            st.caption(f"% {t('change_from_current')}")

    if st.button(t('create_alert'), key="btn_create_alert"):
        if ticker:
            current_price = get_current_price(ticker)
            return {
                'ticker': ticker,
                'alert_type': alert_type,
                'target_value': target_value,
                'base_price': current_price,
                'is_active': True,
                'created_at': datetime.now().isoformat()
            }
        else:
            st.warning(t('enter_ticker'))

    return None


def render_alerts_list(alerts: List[Dict], on_delete=None, on_toggle=None):
    """
    Render list of user's alerts.

    Args:
        alerts: List of alert dictionaries
        on_delete: Callback function when delete is clicked
        on_toggle: Callback function when toggle is clicked
    """
    if not alerts:
        st.info(t('no_alerts'))
        return

    st.subheader(f"🔔 {t('your_alerts')} ({len(alerts)})")

    for idx, alert in enumerate(alerts):
        ticker = alert.get('ticker', 'N/A')
        alert_type = alert.get('alert_type', '')
        target = alert.get('target_value', 0)
        is_active = alert.get('is_active', True)
        base_price = alert.get('base_price')

        # Get current price
        current_price = get_current_price(ticker)
        is_triggered = False
        if current_price:
            is_triggered = check_alert_triggered(alert, current_price)

        # Format alert type label
        type_label = ALERT_TYPE_LABELS.get(AlertType(alert_type), (alert_type, alert_type))[0]

        # Container for each alert
        with st.container():
            cols = st.columns([0.5, 2, 1.5, 1, 1, 0.5])

            # Status indicator
            with cols[0]:
                if is_triggered:
                    st.markdown("🔴")
                elif is_active:
                    st.markdown("🟢")
                else:
                    st.markdown("⚪")

            # Ticker and type
            with cols[1]:
                st.markdown(f"**{ticker}**")
                st.caption(type_label)

            # Target value
            with cols[2]:
                if alert_type in [AlertType.PRICE_ABOVE.value, AlertType.PRICE_BELOW.value]:
                    st.write(f"${target:.2f}")
                else:
                    st.write(f"{target:.1f}%")
                if current_price:
                    diff = current_price - target if alert_type == AlertType.PRICE_ABOVE.value else target - current_price
                    st.caption(f"Now: ${current_price:.2f}")

            # Status
            with cols[3]:
                if is_triggered:
                    st.markdown("**⚠️ TRIGGERED**")
                elif is_active:
                    st.markdown("Active")
                else:
                    st.markdown("Paused")

            # Toggle button
            with cols[4]:
                toggle_label = "⏸️" if is_active else "▶️"
                if st.button(toggle_label, key=f"toggle_alert_{idx}"):
                    if on_toggle:
                        on_toggle(alert.get('id'), not is_active)

            # Delete button
            with cols[5]:
                if st.button("🗑️", key=f"del_alert_{idx}"):
                    if on_delete:
                        on_delete(alert.get('id'))

            st.markdown("---")


def render_triggered_alerts(alerts: List[Dict]):
    """
    Render notification banner for triggered alerts.

    Args:
        alerts: List of alert dictionaries
    """
    triggered = check_user_alerts(alerts)

    if triggered:
        st.warning(f"🔔 **{len(triggered)} {t('alerts_triggered')}!**")

        for alert in triggered:
            ticker = alert.get('ticker')
            alert_type = alert.get('alert_type')
            target = alert.get('target_value')
            current = alert.get('current_price')

            type_label = ALERT_TYPE_LABELS.get(AlertType(alert_type), (alert_type, alert_type))[0]

            if alert_type in [AlertType.PRICE_ABOVE.value, AlertType.PRICE_BELOW.value]:
                st.info(f"📈 **{ticker}**: {type_label} ${target:.2f} (Current: ${current:.2f})")
            else:
                st.info(f"📊 **{ticker}**: {type_label} {target:.1f}% (Current: ${current:.2f})")


def format_alert_message(alert: Dict, current_price: float) -> str:
    """
    Format alert message for display.

    Args:
        alert: Alert dictionary
        current_price: Current stock price

    Returns:
        Formatted message string
    """
    ticker = alert.get('ticker')
    alert_type = alert.get('alert_type')
    target = alert.get('target_value')

    type_label = ALERT_TYPE_LABELS.get(AlertType(alert_type), (alert_type, alert_type))[0]

    if alert_type in [AlertType.PRICE_ABOVE.value, AlertType.PRICE_BELOW.value]:
        return f"{ticker} {type_label} ${target:.2f} | Current: ${current_price:.2f}"
    else:
        base = alert.get('base_price', current_price)
        if base > 0:
            change = ((current_price - base) / base) * 100
            return f"{ticker} {type_label} {target:.1f}% | Change: {change:+.2f}%"
        return f"{ticker} {type_label} {target:.1f}%"
