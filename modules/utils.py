# -*- coding: utf-8 -*-
"""
Utility functions and decorators for the Financial Sankey application.
"""

import time
import pandas as pd
import yfinance as yf
from functools import wraps
from io import BytesIO


def get_yf_ticker(symbol: str) -> yf.Ticker:
    """Create a yfinance Ticker, letting yfinance manage its own session."""
    return yf.Ticker(symbol)


def retry_on_rate_limit(max_retries=5, base_delay=3):
    """Decorator that retries function on rate limit errors with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    if ("too many requests" in error_msg
                            or "rate" in error_msg
                            or "429" in error_msg):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            time.sleep(delay)
                            continue
                    raise e
            return None
        return wrapper
    return decorator


def convert_df_to_excel(df, sheet_name="Data"):
    """Convert DataFrame to Excel bytes for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name)
    return output.getvalue()


def convert_multiple_df_to_excel(dfs_dict):
    """Convert multiple DataFrames to a single Excel file with multiple sheets."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sheets_written = 0
        for sheet_name, df in dfs_dict.items():
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name[:31])  # Excel max sheet name = 31 chars
                sheets_written += 1
        # If no sheets were written, create an empty placeholder sheet
        if sheets_written == 0:
            pd.DataFrame().to_excel(writer, sheet_name="Empty")
    return output.getvalue()


def format_large_number(num):
    """Format large numbers with K, M, B, T suffixes."""
    if num is None:
        return "N/A"
    if abs(num) >= 1e12:
        return f"${num/1e12:.2f}T"
    elif abs(num) >= 1e9:
        return f"${num/1e9:.2f}B"
    elif abs(num) >= 1e6:
        return f"${num/1e6:.2f}M"
    elif abs(num) >= 1e3:
        return f"${num/1e3:.2f}K"
    else:
        return f"${num:.2f}"
