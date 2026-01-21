# -*- coding: utf-8 -*-
"""
Data fetching and processing module for financial data from yfinance.
"""

import pandas as pd
import yfinance as yf
import streamlit as st
import requests
import requests_cache
from fake_useragent import UserAgent
from datetime import timedelta

from modules.utils import retry_on_rate_limit
from modules.logger import log_error, log_warning, log_debug, log_api_call


class DataManager:
    """Class responsible for fetching and processing data from yfinance."""

    @staticmethod
    @st.cache_data(ttl=86400)
    def get_tickers_list():
        """
        Retrieves a list of tickers and filters out potential SPACs based on name.
        """
        all_tickers = set()

        # Keywords typical for companies without revenue (SPAC / Shell / ETFs)
        spac_keywords = ["ACQUISITION", "MERGER", "BLANK CHECK", "CAPITAL CORP", "HOLDINGS CORP", "SPAC", "ETF", "2X", "1X"]

        # Helper function
        def is_clean(name):
            name_upper = str(name).upper()
            for kw in spac_keywords:
                if kw in name_upper:
                    return False
            return True

        # 1. Attempt NASDAQ (Full list)
        try:
            url = "http://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
            df = pd.read_csv(url, sep="|")
            # Remove the last row (often metadata/footer)
            if not df.empty:
                df = df[:-1]

            for _, row in df.iterrows():
                symbol = str(row['Symbol'])
                name = str(row['Security Name'])
                if is_clean(name):
                    all_tickers.add(f"{symbol} | {name}")
            log_debug(f"NASDAQ list loaded: {len(all_tickers)} tickers")
        except Exception as e:
            log_warning(f"Failed to fetch NASDAQ ticker list: {e}")

        # 2. Backup S&P 500 (Always safe)
        try:
            df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
            for _, row in df.iterrows():
                symbol = row['Symbol'].replace('.', '-')
                name = row['Security']
                all_tickers.add(f"{symbol} | {name}")
            log_debug("S&P 500 list loaded")
        except Exception as e:
            log_warning(f"Failed to fetch S&P 500 list: {e}")

        # 3. Backup NASDAQ-100
        try:
            dfs = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')
            for df in dfs:
                # Search for the ticker table
                if 'Ticker' in df.columns or 'Symbol' in df.columns:
                    col_name = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
                    name_col = 'Company' if 'Company' in df.columns else 'Security'

                    if name_col in df.columns:
                        for _, row in df.iterrows():
                            all_tickers.add(f"{row[col_name]} | {row[name_col]}")
                        break
            log_debug("NASDAQ-100 list loaded")
        except Exception as e:
            log_warning(f"Failed to fetch NASDAQ-100 list: {e}")

        # Fallback in case of no internet/errors
        if not all_tickers:
            return ["AAPL | Apple Inc.", "MSFT | Microsoft Corp", "NVDA | Nvidia Corp", "GOOGL | Alphabet Inc."]

        return sorted(list(all_tickers))

    @staticmethod
    def _get_session():
        """Creates a cached session with custom headers to avoid rate limiting."""
        try:
            # Create a cached session (expires after 24 hours)
            # Use a writable path for cache if possible, or just default
            session = requests_cache.CachedSession('yfinance_cache', expire_after=timedelta(hours=24))
        except Exception:
            # Fallback to standard session if cache creation fails
            session = requests.Session()

        # Add a real browser user-agent
        try:
            ua = UserAgent()
            user_agent = ua.random
        except Exception:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session

    @staticmethod
    @st.cache_data(ttl=3600)
    @retry_on_rate_limit(max_retries=3, base_delay=2)
    def get_financials(ticker_symbol):
        try:
            session = DataManager._get_session()
            ticker = yf.Ticker(ticker_symbol, session=session)

            # Force fetching to check if data exists
            income_stmt = ticker.income_stmt
            balance_sheet = ticker.balance_sheet
            info = ticker.info

            # Fetch extras (might fail)
            insider = getattr(ticker, 'insider_purchases', pd.DataFrame())
            recommendations = getattr(ticker, 'recommendations', pd.DataFrame())

            if income_stmt is None or income_stmt.empty:
                return None

            return {
                "income_stmt": income_stmt,
                "balance_sheet": balance_sheet,
                "info": info,
                "insider": insider,
                "recommendations": recommendations
            }
        except Exception as e:
            log_error(e, f"Error fetching data for {ticker_symbol}")
            log_api_call("yfinance", ticker=ticker_symbol, success=False)
            st.error(f"Error fetching data for {ticker_symbol}: {e}")
            return None

    @staticmethod
    def get_available_periods(income_stmt):
        """
        Returns list of available reporting periods from income statement.
        Each period is a tuple: (display_name, column_index)
        """
        if income_stmt is None or income_stmt.empty:
            return []

        periods = []
        for idx, col in enumerate(income_stmt.columns):
            # Format date nicely (e.g., "2024-Q3" or "2024-09")
            if hasattr(col, 'strftime'):
                # Determine quarter
                quarter = (col.month - 1) // 3 + 1
                display_name = f"{col.year}-Q{quarter} ({col.strftime('%Y-%m-%d')})"
            else:
                display_name = str(col)
            periods.append((display_name, idx))

        return periods

    @staticmethod
    def extract_sankey_data(income_stmt, period_index=0, revenue_mod=1.0, cost_mod=1.0):
        """
        Extract detailed data in 'Google-like' style.

        Args:
            income_stmt: DataFrame with income statement data
            period_index: Which period (column) to use (0 = most recent)
            revenue_mod: Revenue modifier for what-if analysis
            cost_mod: Cost modifier for what-if analysis
        """
        try:
            if income_stmt is None or income_stmt.empty:
                return {}

            # Select the specified period (column)
            if period_index >= len(income_stmt.columns):
                period_index = 0
            latest = income_stmt.iloc[:, period_index]

            def get_val(keys):
                for k in keys:
                    if k in latest.index:
                        val = latest[k]
                        return float(val) if pd.notnull(val) else 0.0
                return 0.0

            # 1. Revenue & COGS
            revenue = get_val(["Total Revenue", "Revenue"]) * revenue_mod
            cogs = get_val(["Cost Of Revenue", "Cost of Goods Sold"]) * cost_mod
            gross_profit = revenue - cogs

            # 2. Operating Expenses (Detailed)
            opex_total = get_val(["Operating Expense", "Total Operating Expenses"])
            rnd = get_val(["Research And Development"])
            sga = get_val(["Selling General And Administration"])

            # The rest of OpEx is "Other OpEx"
            other_opex = opex_total - rnd - sga
            if other_opex < 0: other_opex = 0 # Data safety check

            # 3. Operating Profit (Calculated)
            op_profit = gross_profit - opex_total

            # 4. Taxes and Interest
            taxes = get_val(["Tax Provision", "Income Tax Expense"])
            interest = abs(get_val(["Interest Expense", "Interest Income Expense Net"]))

            # 5. Net Income (Calculated for consistency)
            net_income = op_profit - taxes - interest

            return {
                "Revenue": revenue,
                "COGS": cogs,
                "Gross Profit": gross_profit,
                "OpEx_Total": opex_total,
                "R&D": rnd,
                "SG&A": sga,
                "Other OpEx": other_opex,
                "Operating Profit": op_profit,
                "Taxes": taxes,
                "Interest": interest,
                "Net Income": net_income
            }
        except Exception as e:
            log_error(e, "Error processing Sankey data")
            st.error(f"Error processing data: {e}")
            return {}
