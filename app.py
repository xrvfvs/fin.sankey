
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 23 13:56:21 2025

@author: rafal
"""
import openai
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from fpdf import FPDF
import datetime
import os
import urllib.request
import time
import json
from functools import wraps
from io import BytesIO
from supabase import create_client, Client


# --- RETRY DECORATOR FOR RATE LIMITING ---
def retry_on_rate_limit(max_retries=3, base_delay=2):
    """Decorator that retries function on rate limit errors with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "too many requests" in error_msg or "rate" in error_msg:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            time.sleep(delay)
                            continue
                    raise e
            return None
        return wrapper
    return decorator


# --- EXCEL EXPORT HELPER ---
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
        for sheet_name, df in dfs_dict.items():
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name[:31])  # Excel max sheet name = 31 chars
    return output.getvalue()


# --- SUPABASE AUTH HELPER ---
class SupabaseAuth:
    """Helper class for Supabase authentication and user data management."""

    _client = None

    # --- TIER LIMITS CONFIGURATION ---
    TIER_LIMITS = {
        'free': {
            'ai_reports_per_month': 3,
            'watchlist_max': 5,
            'saved_analyses_max': 5,
            'export_enabled': False,
            'historical_periods': 2,  # Only last 2 periods
        },
        'pro': {
            'ai_reports_per_month': 30,
            'watchlist_max': 25,
            'saved_analyses_max': 50,
            'export_enabled': True,
            'historical_periods': None,  # All periods
        },
        'enterprise': {
            'ai_reports_per_month': None,  # Unlimited
            'watchlist_max': None,  # Unlimited
            'saved_analyses_max': None,  # Unlimited
            'export_enabled': True,
            'historical_periods': None,  # All periods
        }
    }

    @classmethod
    def get_tier_limits(cls, tier: str) -> dict:
        """Get limits for a specific tier."""
        return cls.TIER_LIMITS.get(tier, cls.TIER_LIMITS['free'])

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client singleton."""
        if cls._client is None:
            try:
                url = st.secrets["supabase"]["url"]
                key = st.secrets["supabase"]["anon_key"]
                cls._client = create_client(url, key)
            except Exception as e:
                st.error(f"Supabase configuration error: {e}")
                return None
        return cls._client

    @classmethod
    def restore_session(cls):
        """Restore session from session_state if available."""
        client = cls.get_client()
        if client and "supabase_session" in st.session_state:
            session = st.session_state["supabase_session"]
            if session:
                try:
                    client.auth.set_session(session.access_token, session.refresh_token)
                except Exception:
                    pass

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Supabase is properly configured."""
        try:
            return "supabase" in st.secrets and "url" in st.secrets["supabase"]
        except Exception:
            return False

    @classmethod
    def sign_up(cls, email: str, password: str) -> dict:
        """Register a new user."""
        client = cls.get_client()
        if not client:
            return {"error": "Supabase not configured"}
        try:
            response = client.auth.sign_up({
                "email": email,
                "password": password
            })
            if response.user:
                return {"success": True, "user": response.user}
            return {"error": "Registration failed"}
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    def sign_in(cls, email: str, password: str) -> dict:
        """Sign in an existing user."""
        client = cls.get_client()
        if not client:
            return {"error": "Supabase not configured"}
        try:
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if response.user:
                # Store session in session_state for persistence
                st.session_state["supabase_session"] = response.session
                return {"success": True, "user": response.user, "session": response.session}
            return {"error": "Login failed"}
        except Exception as e:
            error_msg = str(e)
            if "Invalid login credentials" in error_msg:
                return {"error": "Invalid email or password"}
            return {"error": error_msg}

    @classmethod
    def sign_out(cls) -> bool:
        """Sign out the current user."""
        client = cls.get_client()
        if not client:
            return False
        try:
            client.auth.sign_out()
            st.session_state.pop("supabase_session", None)
            return True
        except Exception:
            return False

    @classmethod
    def get_user(cls):
        """Get the currently logged in user."""
        client = cls.get_client()
        if not client:
            return None
        try:
            response = client.auth.get_user()
            return response.user if response else None
        except Exception:
            return None

    # --- WATCHLIST METHODS ---
    @classmethod
    def get_watchlist(cls, user_id: str) -> list:
        """Get user's watchlist."""
        client = cls.get_client()
        if not client:
            return []
        try:
            response = client.table("watchlist").select("*").eq("user_id", user_id).execute()
            return response.data if response.data else []
        except Exception:
            return []

    @classmethod
    def add_to_watchlist(cls, user_id: str, ticker: str, company_name: str = None) -> dict:
        """Add ticker to watchlist."""
        client = cls.get_client()
        if not client:
            return {"success": False, "error": "Client not configured"}
        try:
            cls.restore_session()  # Ensure session is active
            response = client.table("watchlist").insert({
                "user_id": user_id,
                "ticker": ticker,
                "company_name": company_name
            }).execute()
            return {"success": True, "data": response.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def remove_from_watchlist(cls, user_id: str, ticker: str) -> bool:
        """Remove ticker from watchlist."""
        client = cls.get_client()
        if not client:
            return False
        try:
            client.table("watchlist").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
            return True
        except Exception:
            return False

    # --- SAVED ANALYSES METHODS ---
    @classmethod
    def save_analysis(cls, user_id: str, ticker: str, report_text: str, citations: list = None, financial_data: dict = None) -> bool:
        """Save an AI analysis report."""
        client = cls.get_client()
        if not client:
            return False
        try:
            client.table("saved_analyses").insert({
                "user_id": user_id,
                "ticker": ticker,
                "report_text": report_text,
                "citations": citations,
                "financial_data": financial_data
            }).execute()
            return True
        except Exception:
            return False

    @classmethod
    def get_saved_analyses(cls, user_id: str) -> list:
        """Get user's saved analyses."""
        client = cls.get_client()
        if not client:
            return []
        try:
            response = client.table("saved_analyses").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception:
            return []

    @classmethod
    def delete_analysis(cls, user_id: str, analysis_id: str) -> bool:
        """Delete a saved analysis."""
        client = cls.get_client()
        if not client:
            return False
        try:
            client.table("saved_analyses").delete().eq("user_id", user_id).eq("id", analysis_id).execute()
            return True
        except Exception:
            return False

    # --- USER PROFILE METHODS ---
    @classmethod
    def get_user_profile(cls, user_id: str) -> dict:
        """Get user profile data."""
        client = cls.get_client()
        if not client:
            return None
        try:
            response = client.table("user_profiles").select("*").eq("id", user_id).single().execute()
            return response.data if response.data else None
        except Exception:
            return None

    # --- TIER LIMIT CHECKING METHODS ---
    @classmethod
    def get_user_tier(cls, user_id: str) -> str:
        """Get user's subscription tier."""
        profile = cls.get_user_profile(user_id)
        if profile:
            return profile.get('subscription_tier', 'free')
        return 'free'

    @classmethod
    def get_user_usage(cls, user_id: str) -> dict:
        """Get user's current usage stats."""
        profile = cls.get_user_profile(user_id)
        if not profile:
            return {'ai_reports_used': 0, 'tier': 'free'}

        return {
            'tier': profile.get('subscription_tier', 'free'),
            'ai_reports_used': profile.get('ai_reports_used', 0),
            'ai_reports_reset_date': profile.get('ai_reports_reset_date'),
        }

    @classmethod
    def can_generate_ai_report(cls, user_id: str) -> dict:
        """Check if user can generate an AI report. Returns dict with 'allowed' and 'message'."""
        usage = cls.get_user_usage(user_id)
        tier = usage.get('tier', 'free')
        limits = cls.get_tier_limits(tier)

        ai_limit = limits.get('ai_reports_per_month')
        ai_used = usage.get('ai_reports_used', 0)

        # None means unlimited
        if ai_limit is None:
            return {'allowed': True, 'used': ai_used, 'limit': None, 'tier': tier}

        if ai_used >= ai_limit:
            return {
                'allowed': False,
                'used': ai_used,
                'limit': ai_limit,
                'tier': tier,
                'message': f"Limit reached ({ai_used}/{ai_limit}). Upgrade to Pro for more reports!"
            }

        return {'allowed': True, 'used': ai_used, 'limit': ai_limit, 'tier': tier}

    @classmethod
    def increment_ai_report_usage(cls, user_id: str) -> bool:
        """Increment the AI report usage counter."""
        client = cls.get_client()
        if not client:
            return False
        try:
            cls.restore_session()
            # Get current usage
            profile = cls.get_user_profile(user_id)
            if not profile:
                return False

            current_count = profile.get('ai_reports_used', 0)

            # Update counter
            client.table("user_profiles").update({
                "ai_reports_used": current_count + 1,
                "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }).eq("id", user_id).execute()
            return True
        except Exception:
            return False

    @classmethod
    def can_add_to_watchlist(cls, user_id: str) -> dict:
        """Check if user can add more items to watchlist."""
        tier = cls.get_user_tier(user_id)
        limits = cls.get_tier_limits(tier)
        watchlist = cls.get_watchlist(user_id)
        current_count = len(watchlist)

        max_limit = limits.get('watchlist_max')

        if max_limit is None:
            return {'allowed': True, 'used': current_count, 'limit': None, 'tier': tier}

        if current_count >= max_limit:
            return {
                'allowed': False,
                'used': current_count,
                'limit': max_limit,
                'tier': tier,
                'message': f"Watchlist full ({current_count}/{max_limit}). Upgrade to Pro!"
            }

        return {'allowed': True, 'used': current_count, 'limit': max_limit, 'tier': tier}

    @classmethod
    def can_save_analysis(cls, user_id: str) -> dict:
        """Check if user can save more analyses."""
        tier = cls.get_user_tier(user_id)
        limits = cls.get_tier_limits(tier)
        analyses = cls.get_saved_analyses(user_id)
        current_count = len(analyses)

        max_limit = limits.get('saved_analyses_max')

        if max_limit is None:
            return {'allowed': True, 'used': current_count, 'limit': None, 'tier': tier}

        if current_count >= max_limit:
            return {
                'allowed': False,
                'used': current_count,
                'limit': max_limit,
                'tier': tier,
                'message': f"Saved analyses limit reached ({current_count}/{max_limit}). Upgrade to Pro!"
            }

        return {'allowed': True, 'used': current_count, 'limit': max_limit, 'tier': tier}

    @classmethod
    def can_export(cls, user_id: str) -> dict:
        """Check if user can export to Excel/PDF."""
        tier = cls.get_user_tier(user_id)
        limits = cls.get_tier_limits(tier)
        allowed = limits.get('export_enabled', False)

        return {
            'allowed': allowed,
            'tier': tier,
            'message': None if allowed else "Export available in Pro tier. Upgrade to unlock!"
        }

    @classmethod
    def get_historical_periods_limit(cls, user_id: str) -> int:
        """Get how many historical periods user can access. None = unlimited."""
        tier = cls.get_user_tier(user_id)
        limits = cls.get_tier_limits(tier)
        return limits.get('historical_periods')

    # --- GLOBAL REPORTS CACHE METHODS ---
    GLOBAL_CACHE_TTL_DAYS = 7  # Reports valid for 7 days

    @classmethod
    def get_global_cached_report(cls, ticker: str) -> dict:
        """Get report from global cache if exists and not expired."""
        client = cls.get_client()
        if not client:
            return None
        try:
            response = client.table("global_reports_cache").select("*").eq("ticker", ticker).single().execute()
            if response.data:
                # Check if cache is still valid
                created_at = datetime.datetime.fromisoformat(response.data['created_at'].replace('Z', '+00:00'))
                age_days = (datetime.datetime.now(datetime.timezone.utc) - created_at).days
                if age_days <= cls.GLOBAL_CACHE_TTL_DAYS:
                    return {
                        "text": response.data.get("report_text"),
                        "citations": response.data.get("citations"),
                        "age_days": age_days,
                        "from_cache": "global"
                    }
            return None
        except Exception:
            return None

    @classmethod
    def save_to_global_cache(cls, ticker: str, report_text: str, citations: list = None, financial_snapshot: dict = None) -> bool:
        """Save or update report in global cache."""
        client = cls.get_client()
        if not client:
            return False
        try:
            cls.restore_session()  # Ensure authenticated
            # Upsert - insert or update if exists
            client.table("global_reports_cache").upsert({
                "ticker": ticker,
                "report_text": report_text,
                "citations": citations,
                "financial_snapshot": financial_snapshot,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }, on_conflict="ticker").execute()
            return True
        except Exception as e:
            return False

    @classmethod
    def get_best_cached_report(cls, ticker: str, user_id: str = None) -> dict:
        """
        Get best available cached report. Priority:
        1. Global cache (if < 7 days old)
        2. User's saved analysis (if logged in)
        3. None (need to generate new)
        """
        # Try global cache first
        global_report = cls.get_global_cached_report(ticker)
        if global_report:
            return global_report

        # Try user's saved analyses
        if user_id:
            saved = cls.get_saved_analyses(user_id)
            for analysis in saved:
                if analysis.get('ticker') == ticker:
                    return {
                        "text": analysis.get("report_text"),
                        "citations": analysis.get("citations"),
                        "from_cache": "user_saved"
                    }

        return None


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="san.key - Advanced Financial Viz",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. DATA FETCHING MODULE ---
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
        except Exception: 
            pass

        # 2. Backup S&P 500 (Always safe)
        try:
            df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
            for _, row in df.iterrows():
                symbol = row['Symbol'].replace('.', '-')
                name = row['Security']
                all_tickers.add(f"{symbol} | {name}")
        except Exception: 
            pass
            
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
        except Exception: 
            pass

        # Fallback in case of no internet/errors
        if not all_tickers:
            return ["AAPL | Apple Inc.", "MSFT | Microsoft Corp", "NVDA | Nvidia Corp", "GOOGL | Alphabet Inc."]

        return sorted(list(all_tickers))

    @staticmethod
    @st.cache_data(ttl=3600)
    @retry_on_rate_limit(max_retries=3, base_delay=2)
    def get_financials(ticker_symbol):
        try:
            ticker = yf.Ticker(ticker_symbol)

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
            st.error(f"Error processing data: {e}")
            return {}

# --- 2. VISUALIZATION MODULE ---
class Visualizer:
    """Visualization class in App Economy Insights style."""
    
    @staticmethod
    def _fmt(val):
        """Helper number formatter (e.g., 50B)."""
        if val >= 1e12: return f"${val/1e12:.1f}T"
        if val >= 1e9: return f"${val/1e9:.1f}B"
        if val >= 1e6: return f"${val/1e6:.1f}M"
        return f"${val:.0f}"

    @staticmethod
    def plot_sankey(data, title_suffix=""):
        if not data: return go.Figure()
        
        # NODE DEFINITIONS
        # Indices:
        # 0: Revenue, 1: Gross Profit, 2: Cost of Revenue
        # 3: Operating Profit, 4: R&D, 5: SG&A, 6: Other OpEx
        # 7: Net Income, 8: Tax, 9: Interest
        
        labels = [
            f"Revenue<br>{Visualizer._fmt(data['Revenue'])}",           # 0
            f"Gross Profit<br>{Visualizer._fmt(data['Gross Profit'])}", # 1
            f"Cost of Rev<br>{Visualizer._fmt(data['COGS'])}",          # 2
            f"Op Profit<br>{Visualizer._fmt(data['Operating Profit'])}",# 3
            f"R&D<br>{Visualizer._fmt(data['R&D'])}",                   # 4
            f"SG&A<br>{Visualizer._fmt(data['SG&A'])}",                 # 5
            f"Other OpEx<br>{Visualizer._fmt(data['Other OpEx'])}",     # 6
            f"Net Income<br>{Visualizer._fmt(data['Net Income'])}",     # 7
            f"Tax<br>{Visualizer._fmt(data['Taxes'])}",                 # 8
            f"Interest<br>{Visualizer._fmt(data['Interest'])}"          # 9
        ]
        
        # NODE COLORS (Modeled after Google/Alphabet charts)
        # Revenue=Blue, Profits=Green, Costs=Red
        c_rev = "#4285F4"  # Google Blue
        c_prof = "#34A853" # Google Green
        c_cost = "#EA4335" # Google Red
        c_sub = "#FBBC05"  # Google Yellow (for Interest/Other)
        
        node_colors = [
            c_rev, c_prof, c_cost,  # 0, 1, 2
            c_prof, c_cost, c_cost, c_cost, # 3, 4, 5, 6
            c_prof, c_cost, c_sub   # 7, 8, 9
        ]

        # LINK DEFINITIONS
        source = []
        target = []
        value = []
        link_color = []
        
        # Helper function to add colored links
        def add_link(src, tgt, val, type="neutral"):
            if val > 0:
                source.append(src)
                target.append(tgt)
                value.append(val)
                # Semi-transparent link colors
                if type == "profit": link_color.append("rgba(52, 168, 83, 0.4)") # Green alpha
                elif type == "cost": link_color.append("rgba(234, 67, 53, 0.4)") # Red alpha
                else: link_color.append("rgba(66, 133, 244, 0.3)") # Blue alpha

        # 1. Revenue -> Gross Profit (Profit) & COGS (Cost)
        add_link(0, 1, data['Gross Profit'], "profit")
        add_link(0, 2, data['COGS'], "cost")
        
        # 2. Gross Profit -> Op Profit (Profit) & OpEx (Costs)
        add_link(1, 3, data['Operating Profit'], "profit")
        # OpEx Breakdown
        add_link(1, 4, data['R&D'], "cost")
        add_link(1, 5, data['SG&A'], "cost")
        add_link(1, 6, data['Other OpEx'], "cost")
        
        # 3. Op Profit -> Net Income (Profit) & Tax/Interest (Costs)
        add_link(3, 7, data['Net Income'], "profit")
        add_link(3, 8, data['Taxes'], "cost")
        add_link(3, 9, data['Interest'], "cost")

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20, thickness=20,
                line=dict(color="white", width=0.5),
                label=labels,
                color=node_colors,
                hovertemplate='%{label}<extra></extra>' # Clean hover
            ),
            link=dict(
                source=source, target=target, value=value,
                color=link_color
            )
        )])
        
        fig.update_layout(
            title_text=f"<b>Income Statement Flow</b> {title_suffix}", 
            font_size=13, height=600,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig

    @staticmethod
    def plot_waterfall(data, title_suffix=""):
        if not data: return go.Figure()
        
        # Waterfall with consistent color logic
        vals = [
            data['Revenue'], -data['COGS'], data['Gross Profit'], 
            -data['R&D'], -data['SG&A'], -data['Other OpEx'],
            data['Operating Profit'], -data['Taxes'], -data['Interest'], data['Net Income']
        ]
        
        names = [
            "Revenue", "COGS", "Gross Profit", 
            "R&D", "SG&A", "Other OpEx", 
            "Op Profit", "Tax", "Interest", "Net Income"
        ]
        
        # Bar coloring: Totals=Blue (or Green), Minus=Red, Plus=Green
        measure = ["absolute", "relative", "total", "relative", "relative", "relative", "total", "relative", "relative", "total"]
        
        fig = go.Figure(go.Waterfall(
            name="Income", orientation="v",
            measure=measure,
            x=names,
            y=vals,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#EA4335"}}, # Red
            increasing={"marker": {"color": "#34A853"}}, # Green
            totals={"marker": {"color": "#34A853"}}      # Green (Profit)
        ))

        fig.update_layout(title=f"<b>Profit & Loss Waterfall</b> {title_suffix}", height=600)
        return fig

    @staticmethod
    def plot_sentiment(recommendations):
        """(No changes needed)"""
        try:
            if recommendations.empty: return None
            rec_counts = recommendations.iloc[:, 0:4].sum()
            fig = go.Figure(data=[go.Bar(x=rec_counts.index, y=rec_counts.values)])
            fig.update_layout(title="Analyst Recommendations", height=300)
            return fig
        except: return None

    @staticmethod
    def _format_financial_value(val):
        """Format value with B/M/K suffix for financial display."""
        if val is None:
            return "N/A"
        abs_val = abs(val)
        sign = "-" if val < 0 else ""
        if abs_val >= 1e9:
            return f"{sign}${abs_val/1e9:.1f}B"
        elif abs_val >= 1e6:
            return f"{sign}${abs_val/1e6:.0f}M"
        elif abs_val >= 1e3:
            return f"{sign}${abs_val/1e3:.0f}K"
        else:
            return f"{sign}${abs_val:,.0f}"

    @staticmethod
    def plot_historical_trend(income_stmt, metrics=None):
        """
        Creates a line chart showing historical trends of key financial metrics.

        Args:
            income_stmt: DataFrame with income statement (columns = periods)
            metrics: List of metrics to plot. If None, uses defaults.
        """
        if income_stmt is None or income_stmt.empty:
            return go.Figure()

        # Default metrics to track
        if metrics is None:
            metrics = [
                ("Total Revenue", "Revenue"),
                ("Gross Profit", "Gross Profit"),
                ("Operating Income", "Operating Income"),
                ("Net Income", "Net Income")
            ]

        fig = go.Figure()

        # Colors for different metrics
        colors = ["#4285F4", "#34A853", "#FBBC05", "#EA4335"]

        all_values = []  # Collect all values to determine scale

        for i, (metric_key, metric_name) in enumerate(metrics):
            # Try to find the metric in the income statement
            if metric_key in income_stmt.index:
                values = income_stmt.loc[metric_key].values
                all_values.extend(values)

                # Format dates for x-axis (reverse to show oldest first)
                dates = []
                for col in income_stmt.columns:
                    if hasattr(col, 'strftime'):
                        quarter = (col.month - 1) // 3 + 1
                        dates.append(f"{col.year}-Q{quarter}")
                    else:
                        dates.append(str(col))

                # Reverse to show chronological order (oldest to newest)
                dates_rev = dates[::-1]
                values_rev = values[::-1]

                # Format hover values with B/M suffix
                hover_texts = [Visualizer._format_financial_value(v) for v in values_rev]

                fig.add_trace(go.Scatter(
                    x=dates_rev,
                    y=values_rev,
                    name=metric_name,
                    mode='lines+markers',
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=8),
                    hovertemplate=f'{metric_name}: %{{text}}<extra></extra>',
                    text=hover_texts
                ))

        # Determine scale for y-axis labels
        if all_values:
            max_abs = max(abs(v) for v in all_values if v is not None)
            if max_abs >= 1e9:
                divisor, suffix = 1e9, "B"
            elif max_abs >= 1e6:
                divisor, suffix = 1e6, "M"
            else:
                divisor, suffix = 1, ""
        else:
            divisor, suffix = 1, ""

        fig.update_layout(
            title="<b>Historical Financial Trends</b>",
            xaxis_title="Period",
            yaxis_title=f"Value (${suffix})",
            height=400,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=60, r=20, t=60, b=20)
        )

        # Scale y-axis values for cleaner display
        if divisor > 1:
            fig.update_yaxes(
                tickformat=".1f",
                ticksuffix=suffix,
                tickprefix="$"
            )
            # Update trace y-values to be in scaled units
            for trace in fig.data:
                trace.y = [v / divisor if v is not None else None for v in trace.y]

        return fig

    @staticmethod
    def calculate_yoy_metrics(income_stmt):
        """
        Calculates Year-over-Year changes for key metrics.
        Compares most recent period with the previous period (index 0 vs index 1).

        Returns dict with metric name -> (current_value, yoy_change_pct)
        """
        if income_stmt is None or income_stmt.empty:
            return {}

        if len(income_stmt.columns) < 2:
            return {}

        results = {}
        metrics_to_calc = [
            ("Total Revenue", "Revenue"),
            ("Gross Profit", "Gross Profit"),
            ("Operating Income", "Operating Income"),
            ("Net Income", "Net Income")
        ]

        for metric_key, metric_name in metrics_to_calc:
            if metric_key in income_stmt.index:
                current = income_stmt.loc[metric_key].iloc[0]
                # Compare with previous period (index 1 = previous year for annual data)
                previous = income_stmt.loc[metric_key].iloc[1]

                if previous and previous != 0:
                    yoy_change = ((current - previous) / abs(previous)) * 100
                else:
                    yoy_change = None

                results[metric_name] = (current, yoy_change)

        return results


class PDFReport(FPDF):
    """Rozszerzona klasa FPDF do obsługi Markdown i Unicode."""

    font_family = 'Helvetica'  # Default fallback font

    def header(self):
        try:
            self.set_font(PDFReport.font_family, '', 10)
        except Exception:
            self.set_font('Helvetica', '', 10)
        self.cell(0, 10, 'AI Report', 0, 1, 'R')
        self.ln(5)

    def chapter_title(self, label):
        try:
            self.set_font(PDFReport.font_family, 'B', 14)
        except Exception:
            self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, label, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, text):
        try:
            self.set_font(PDFReport.font_family, '', 11)
        except Exception:
            self.set_font('Helvetica', '', 11)
        self.multi_cell(0, 6, text)
        self.ln()

class ReportGenerator:
    """Generowanie raportów PDF i analizy AI (Perplexity API) z cytowaniami."""

    CACHE_DIR = ".report_cache"
    CACHE_TTL_HOURS = 24  # Reports are valid for 24 hours

    @staticmethod
    def _get_cache_path(ticker):
        """Returns the cache file path for a given ticker."""
        os.makedirs(ReportGenerator.CACHE_DIR, exist_ok=True)
        return os.path.join(ReportGenerator.CACHE_DIR, f"{ticker}_report.json")

    @staticmethod
    def get_cached_report(ticker):
        """
        Returns cached report if it exists and is not expired.
        Returns tuple: (report_data, cache_age_hours) or (None, None)
        """
        cache_path = ReportGenerator._get_cache_path(ticker)

        if not os.path.exists(cache_path):
            return None, None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check cache age
            cached_time = datetime.datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            age = datetime.datetime.now() - cached_time
            age_hours = age.total_seconds() / 3600

            if age_hours > ReportGenerator.CACHE_TTL_HOURS:
                return None, None  # Cache expired

            return cache_data.get('report'), age_hours
        except Exception:
            return None, None

    @staticmethod
    def save_report_to_cache(ticker, report_data):
        """Saves report data to cache file."""
        cache_path = ReportGenerator._get_cache_path(ticker)

        try:
            cache_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'ticker': ticker,
                'report': report_data
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def ensure_font_exists():
        """Pobiera czcionkę DejaVuSans.ttf jeśli nie istnieje."""
        font_path = "DejaVuSans.ttf"
        if not os.path.exists(font_path):
            url = "https://github.com/reingart/pyfpdf/raw/master/fpdf/font/DejaVuSans.ttf"
            try:
                urllib.request.urlretrieve(url, font_path)
            except:
                pass 
        return font_path

    @staticmethod
    def clean_text(text):
        """Kompleksowe czyszczenie tekstu z niebezpiecznych znaków Unicode i naprawa sklejonych słów."""
        if not isinstance(text, str):
            return str(text)

        import re

        replacements = {
            # --- NAPRAWA SKLEJONYCH SŁÓW ---
            '\u200b': '',    # Zero-width space -> usuwamy
            '\u200c': '',    # Zero-width non-joiner
            '\u200d': '',    # Zero-width joiner
            '\ufeff': '',    # BOM / zero-width no-break space
            '\xa0': ' ',     # Non-breaking space -> spacja

            # --- NAPRAWA DZIWNYCH GWIAZDEK ---
            '∗': '*',        # Operator matematyczny -> zwykła gwiazdka
            '\u2217': '*',   # To samo (kod unicode)

            # --- STANDARDOWE ZAMIENNIKI ---
            '\u2013': '-', '\u2014': '-', '\u2011': '-',
            '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
            '\u2022': '*', '\u2026': '...',
            '\u2248': '~', '\u2260': '!=', '\u2264': '<=', '\u2265': '>=',
            '\u2191': '^', '\u2193': 'v', '\u2192': '->',
            '€': 'EUR', '£': 'GBP', '¥': 'JPY',
        }

        for char, repl in replacements.items():
            text = text.replace(char, repl)

        # Usunięcie innych zero-width i niewidocznych znaków Unicode
        text = re.sub(r'[\u200b-\u200f\u2028-\u202f\u2060-\u206f]', '', text)

        # Dodatkowa naprawa: spacja po kropce, jeśli jej brakuje (np. "share.We")
        text = re.sub(r'\.(?=[A-Z])', '. ', text)

        # Naprawa $X.XXvalue -> $X.XX value (liczby sklejone ze słowami)
        text = re.sub(r'(\$[\d,.]+)([a-zA-Z])', r'\1 \2', text)

        # Usuwanie podwójnych spacji
        text = re.sub(r' +', ' ', text)

        try:
            return text.encode('latin-1', 'replace').decode('latin-1')
        except:
            return text

    # ... (metody generate_ai_prompt i get_ai_analysis bez zmian - skopiuj je z poprzedniej wersji) ...
    @staticmethod
    def generate_ai_prompt(ticker, data, info):
        # SKOPIUJ Z POPRZEDNIEJ WERSJI
        revenue = data.get('Revenue', 0)
        net_income = data.get('Net Income', 0)
        gross_profit = data.get('Gross Profit', 0)
        gross_margin = (gross_profit / revenue * 100) if revenue else 0
        
        # Pobieranie waluty (jeśli dostępna, domyślnie USD)
        currency = info.get('currency', 'USD')
        # --- POPRAWKA ---
        # 1. Cena jest w 'info', a nie w 'data'.
        # 2. Używamy standardowych kluczy yfinance.
        current_price = info.get('currentPrice')
        
        # Zabezpieczenie (fallback): jeśli nie ma 'currentPrice', szukaj 'regularMarketPrice' lub 'previousClose'
        if not current_price:
            current_price = info.get('regularMarketPrice') or info.get('previousClose') or 0

        prompt = f"""
       Przygotuj obszerny, profesjonalny EQUITY RESEARCH REPORT o spółce: {ticker} w języku angielskim.

ROLA:
Jesteś starszym analitykiem (Senior Equity Analyst) w banku inwestycyjnym Tier-1 (np. Goldman Sachs, Morgan Stanley). Twój styl pisania musi być "instytucjonalny": zwięzły, oparty na danych, nastawiony na wnioski inwestycyjne (actionable insights), a nie na opowiadanie historii.

DANE FUNDAMENTALNE (WSAD):

Przychody (LTM): {revenue:,.0f} {currency}

Zysk Netto (LTM): {net_income:,.0f} {currency}

Marża Brutto: {gross_margin:.2f}%

P/E Ratio: {info.get('trailingPE', 'N/A')}

Debt/Equity: {info.get('debtToEquity', 'N/A')}

PEG Ratio: {info.get('pegRatio', 'N/A')}

STRUKTURA RAPORTU (Ściśle zachowaj kolejność i formatowanie):

1. INVESTMENT THESIS 

Masthead (Nagłówek): Stwórz tabelę na samej górze z kluczowymi danymi:

Rating (np. BUY / HOLD / SELL - wyróżnione)

Price Target (Cena docelowa)

Current Price  {current_price} {currency}

Implied Upside/Downside (%)

Risk Profile (np. High/Medium)

Investment Thesis: To jest najważniejsza sekcja. Nie pisz "wstępu". Od razu podaj główne argumenty za rekomendacją. Dlaczego teraz? Co rynek przeoczył? (Max 3-4 mocne akapity).

Catalyst Watch: Krótka lista z datami (np. nadchodzące wyniki, decyzje regulacyjne, premiery produktów), które mogą ruszyć kursem w najbliższych 6 miesiącach.

2. FINANCIAL ESTIMATES & SUMMARY (Tabela prognoz)

Zamiast ściany tekstu, stwórz tabelę Markdown "Financial Summary Estimates" prognozującą wyniki na 3 lata w przód (np. 2026E, 2027E, 2028E). Uwzględnij: Revenue, EBITDA, EPS, P/E Ratio, FCF Yield.

Pod tabelą krótki komentarz analityczny dotyczący dynamiki wzrostu i dźwigni operacyjnej.

3. VALUATION (Szczegółowa wycena)

Metodologia: Zastosuj podejście hybrydowe (DCF + Multiples).

SOTP Table (Sum-of-the-Parts): Jeśli spółka ma różne segmenty, KONIECZNIE stwórz tabelę SOTP wyceniającą każdy segment osobno (np. Segment A x Multiple + Segment B x Multiple = Enterprise Value). Jeśli SOTP nie pasuje, zrób tabelę "Valuation Matrix" pokazującą implikowaną cenę przy różnych założeniach WACC i Terminal Growth.

Krótkie uzasadnienie przyjętych mnożników (dlaczego taki P/E lub EV/EBITDA?).

4. SCENARIUSZE CENOWE (Bull / Base / Bear)
Zamiast opisów, przedstaw to w formie tabeli lub listy z przypisanym prawdopodobieństwem:

Bull Case ($XXX): Co musi się udać perfekcyjnie? (np. szybsza adopcja produktu, wzrost marży). Prawdopodobieństwo (np. 20%).

Base Case ($XXX): Twój główny scenariusz. Prawdopodobieństwo (np. 50%).

Bear Case ($XXX): Co pójdzie nie tak? (np. recesja, utrata klienta). Prawdopodobieństwo (np. 30%).

5. KEY RISKS (Ryzyka inwestycyjne)

Konkretne i punktowe (np. ryzyko regulacyjne, koncentracja klientów, ryzyko walutowe). Unikaj ogólników typu "ryzyko rynkowe".

6. SEGMENT ANALYSIS (Analiza operacyjna)

Krótki przegląd wyników per segment/geografia.

Skup się na rentowności i trendach (np. "Segment X rośnie o 20% r/r, ale marże spadają").

7. APPENDIX & DISCLOSURES

Dodaj profesjonalną notkę prawną (Disclaimer) na końcu: "For sophisticated investors only. This report is for educational purposes and does not constitute financial advice."

Analyst Certification: Oświadczenie, że opinie są własne.

WYMAGANIA TECHNICZNE:

Język raportu: Angielski (Profesjonalny żargon finansowy).

Formatowanie: Używaj Markdown do tworzenia tabel, pogrubień i nagłówków.

Styl: "Bottom-line up front" (wnioski na początku). Używaj strony czynnej.

Nie cytuj dosłownie, parafrazuj i syntezuj. 
        """
        return prompt

    @staticmethod
    def get_ai_analysis(api_key, prompt):
        # SKOPIUJ Z POPRZEDNIEJ WERSJI
        try:
            client = openai.OpenAI(
                api_key=api_key, 
                base_url="https://api.perplexity.ai"
            )
            response = client.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10000
            )
            content = response.choices[0].message.content
            citations = getattr(response, 'citations', [])
            return content, citations
        except Exception as e:
            return f"❌ Błąd API: {str(e)}", []
    @staticmethod
    def draw_professional_table(pdf, table_data, title="", col_widths=None, max_width=190):
        """
        Rysuje profesjonalną tabelę w PDF z zawijaniem tekstu i automatycznym dostosowaniem.
        
        Args:
            pdf: Obiekt FPDF
            table_data: Lista list (pierwsza = nagłówek, reszta = wiersze)
            title: Opcjonalny tytuł tabeli
            col_widths: Lista szerokości kolumn. Jeśli None, oblicza automatycznie.
            max_width: Maksymalna dostępna szerokość (domyślnie 190mm)
        """
        
        if not table_data or len(table_data) == 0:
            return
            
        # Konwersja wszystkich danych do stringów i czyszczenie
        table_data = [[ReportGenerator.clean_text(str(cell)) for cell in row] for row in table_data]
        
        num_cols = len(table_data[0])
        num_rows = len(table_data)
        
        # --- KROK 1: Automatyczne obliczanie szerokości kolumn ---
        if col_widths is None:
            col_widths = [max_width / num_cols] * num_cols  # Domyślnie równa szerokość
        else:
            # Normalizuj do całkowitej szerokości max_width
            total = sum(col_widths)
            col_widths = [(w / total) * max_width for w in col_widths]
        
        # --- KROK 2: Sprawdź czy tabela zmieści się na stronie ---
        required_height = ReportGenerator._estimate_table_height(
            table_data, col_widths, font_size=9
        )
        
        # Jeśli brakuje miejsca, dodaj nową stronę
        if pdf.get_y() + required_height > pdf.h - pdf.b_margin:
            pdf.add_page()
        
        # --- KROK 3: Rysuj tytuł (opcjonalnie) ---
        if title:
            pdf.set_font('DejaVu', 'B', 11)
            pdf.cell(0, 8, title, 0, 1, 'L')
            pdf.ln(2)
        
        # --- KROK 4: Rysuj nagłówek ---
        y_start = pdf.get_y()
        header = table_data[0]
        row_height = ReportGenerator._draw_table_row(
            pdf, header, col_widths, 
            font_size=9, 
            is_header=True, 
            bg_color=(200, 200, 200)
        )
        
        # --- KROK 5: Rysuj wiersze danych ---
        for i, row in enumerate(table_data[1:]):
            # Pad row if needed
            while len(row) < num_cols:
                row.append("")
            
            # Zmiennie kolory rzędów (zebra stripe dla lepszej czytelności)
            bg_color = (245, 245, 245) if i % 2 == 0 else (255, 255, 255)
            
            row_height = ReportGenerator._draw_table_row(
                pdf, row, col_widths, 
                font_size=9, 
                is_header=False, 
                bg_color=bg_color
            )
        
        pdf.ln(4)
    
    @staticmethod
    def _draw_table_row(pdf, cells, col_widths, font_size=9, is_header=False, bg_color=None):
        """
        Rysuje pojedynczy wiersz tabeli z Multi-cell zawijaniem.
        Zwraca wysokość wiersza.
        """
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # Ustaw font
        font_style = 'B' if is_header else ''
        pdf.set_font('DejaVu', font_style, font_size)
        
        # Krok 1: Oblicz wysokość wiersza (maksymalna z wszystkich kolumn)
        line_heights = []
        for i, text in enumerate(cells):
            col_w = col_widths[i]
            x, y = pdf.get_x(), pdf.get_y()
            
            # Tymczasowe multi_cell do obliczenia wysokości
            pdf.multi_cell(col_w, 5, text, border=0)
            new_y = pdf.get_y()
            
            height = new_y - y
            line_heights.append(height)
            pdf.set_xy(x, y)
        
        row_height = max(line_heights) if line_heights else 5
        
        # Krok 2: Rysuj tło i obramowanie
        x = x_start
        for i, col_w in enumerate(col_widths):
            if bg_color:
                pdf.set_fill_color(*bg_color)
                pdf.rect(x, y_start, col_w, row_height, 'FD')
            else:
                pdf.rect(x, y_start, col_w, row_height)
            x += col_w
        
        # Krok 3: Wpisz tekst do komórek
        x = x_start
        for i, text in enumerate(cells):
            col_w = col_widths[i]
            pdf.set_xy(x, y_start + 1)
            
            # Wyrównanie: nagłówek do środka, dane do lewej
            align = 'C' if is_header else 'L'
            pdf.multi_cell(col_w, 5, text, border=0, align=align)
            
            x += col_w
        
        # Ustaw pozycję na koniec wiersza
        pdf.set_xy(x_start, y_start + row_height)
        
        return row_height
    
    @staticmethod
    def _estimate_table_height(table_data, col_widths, font_size=9):
        """Estymuje wysokość tabeli (przybliżenie dla sprawdzenia czy zmieści się na stronie)."""
        # Prosta heurystyka: 6 px na linię tekstu + marża
        num_rows = len(table_data)
        avg_height_per_row = 15  # pixels
        return num_rows * avg_height_per_row + 10  # +10 dla marginesu


    
    @staticmethod
    def create_pdf(ticker, analysis_text, metrics, citations=[]):
        # 1. Przygotowanie fontów i czyszczenie tekstu
            font_path = ReportGenerator.ensure_font_exists()
            analysis_text = ReportGenerator.clean_text(analysis_text)

            # Reset font to default before trying to load DejaVu
            PDFReport.font_family = 'Helvetica'

            pdf = PDFReport()
            font_loaded = False
            try:
                if os.path.exists(font_path):
                    pdf.add_font('DejaVu', '', font_path, uni=True)
                    pdf.add_font('DejaVu', 'B', font_path, uni=True)
                    font_loaded = True
                    PDFReport.font_family = 'DejaVu'
            except Exception:
                font_loaded = False
                PDFReport.font_family = 'Helvetica'

            pdf.add_page()

            # Funkcja pomocnicza do ustawiania fontu
            def set_safe_font(family, style, size):
                try:
                    if font_loaded and family == 'DejaVu':
                        pdf.set_font('DejaVu', style, size)
                    else:
                        pdf.set_font('Helvetica', style, size)
                except Exception:
                    pdf.set_font('Helvetica', style, size)
    
            # --- NOWA FUNKCJA: Drukowanie z obsługą **POGRUBIENIA** ---
            def print_formatted_text(text):
                """
                Parsuje tekst:
                - Zamienia **tekst** na pogrubienie
                - Usuwa znaki _ (kursywa), bo nie mamy załadowanego fontu Italic
                - Używa pdf.write() zamiast multi_cell() dla płynnego tekstu
                """
                # Usuwamy kursywę (podłogi), żeby nie śmieciły (DejaVu w tym kodzie nie ma załadowanego stylu 'I')
                text = text.replace('_', '')
                
                # Dzielimy tekst po znaczniku pogrubienia '**'
                # Co drugi element tablicy będzie tym, który ma być pogrubiony
                parts = text.split('**')
                
                for i, part in enumerate(parts):
                    if i % 2 == 1:
                        # Nieparzyste indeksy to tekst wewnątrz **...** -> POGRUBIAMY
                        set_safe_font('DejaVu', 'B', 11)
                        pdf.write(5, part)
                    else:
                        # Parzyste to zwykły tekst
                        set_safe_font('DejaVu', '', 11)
                        pdf.write(5, part)
                
                # Na koniec akapitu przejście do nowej linii + odstęp
                pdf.ln(6)
    
            # --- FUNKCJA RYSUJĄCA WIERSZ TABELI ---
            def draw_table_row(cells, col_widths, is_header=False):
                if is_header: set_safe_font('DejaVu', 'B', 9)
                else: set_safe_font('DejaVu', '', 9)
    
                # KROK 1: Obliczanie wysokości (Symulacja na biało)
                pdf.set_text_color(255, 255, 255)
                original_auto_page_break = pdf.auto_page_break
                pdf.set_auto_page_break(False)
                
                line_heights = []
                sim_y_start = pdf.get_y()
                sim_x_start = pdf.l_margin
                
                for i, text in enumerate(cells):
                    col_w = col_widths[i] if i < len(col_widths) else (190 / len(cells))
                    pdf.set_xy(sim_x_start, sim_y_start)
                    y_before = pdf.get_y()
                    pdf.multi_cell(col_w, 5, str(text), border=0)
                    y_after = pdf.get_y()
                    line_heights.append(y_after - y_before)
                    sim_x_start += col_w
    
                pdf.set_text_color(0, 0, 0) # Powrót do czarnego
                pdf.set_auto_page_break(original_auto_page_break, margin=10)
                pdf.set_xy(pdf.l_margin, sim_y_start)
    
                row_height = max(line_heights) if line_heights else 5
                row_height = max(row_height, 5)
    
                if pdf.get_y() + row_height > pdf.h - 15:
                    pdf.add_page()
                    if is_header: set_safe_font('DejaVu', 'B', 9)
                    else: set_safe_font('DejaVu', '', 9)
    
                # KROK 2: Rysowanie
                y_start = pdf.get_y()
                x_start = pdf.l_margin
                
                for i, text in enumerate(cells):
                    col_w = col_widths[i] if i < len(col_widths) else (190 / len(cells))
                    pdf.set_xy(x_start, y_start)
                    pdf.rect(x_start, y_start, col_w, row_height)
                    align_mode = 'C' if is_header else 'L'
                    pdf.multi_cell(col_w, 5, str(text), border=0, align=align_mode)
                    x_start += col_w
    
                pdf.set_xy(pdf.l_margin, y_start + row_height)
    
            # ---------------------------------------------------------
            # BUDOWANIE RAPORTU
            # ---------------------------------------------------------
            
            set_safe_font('DejaVu', 'B', 16)
            pdf.cell(0, 10, txt=f"AI Investment Report: {ticker}", ln=1, align='C')
            pdf.ln(5)
            
            pdf.set_fill_color(240, 240, 240)
            if metrics:
                pdf.rect(10, pdf.get_y(), 190, 20, 'F')
                set_safe_font('DejaVu', '', 10)
                pdf.set_y(pdf.get_y() + 5)
                col_width = 190 / max(1, len(metrics))
                for k, v in metrics.items():
                    clean_k = ReportGenerator.clean_text(str(k))
                    clean_v = ReportGenerator.clean_text(str(v))
                    if not font_loaded:
                        clean_k = clean_k.encode('latin-1', 'ignore').decode('latin-1')
                        clean_v = clean_v.encode('latin-1', 'ignore').decode('latin-1')
                    pdf.cell(col_width, 10, f"{clean_k}: {clean_v}", 0, 0, 'C')
                pdf.ln(20)
    
            set_safe_font('DejaVu', '', 11)
            lines = analysis_text.split('\n')
            in_table = False
            table_header = []
            table_rows = []
    
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Tabela
                if line.startswith('|'):
                    in_table = True
                    cells = [ReportGenerator.clean_text(c.strip()) for c in line.split('|')]
                    if cells and cells[0] == '': cells.pop(0)
                    if cells and cells[-1] == '': cells.pop(-1)
                    
                    if '---' in line: continue
                    if not table_header: table_header = cells
                    else: table_rows.append(cells)
                    continue
                
                if (in_table and not line.startswith('|')) or (in_table and i == len(lines)-1):
                    in_table = False
                    if table_header:
                        pdf.ln(2)
                        num_cols = len(table_header)
                        col_w = 190 / max(1, num_cols)
                        col_widths = [col_w] * num_cols
                        draw_table_row(table_header, col_widths, is_header=True)
                        for row in table_rows:
                            while len(row) < num_cols: row.append("")
                            draw_table_row(row[:num_cols], col_widths, is_header=False)
                        pdf.ln(5)
                    table_header = []
                    table_rows = []
                    set_safe_font('DejaVu', '', 11)
    
                if not line:
                    if not in_table: pdf.ln(2)
                    continue
                if in_table: continue
    
                if not font_loaded:
                    line = line.encode('latin-1', 'replace').decode('latin-1')
    
                # --- RENDEROWANIE TREŚCI ---
                if line.startswith('#'):
                    set_safe_font('DejaVu', 'B', 12)
                    pdf.cell(0, 8, line.lstrip('#').strip(), 0, 1)
                    set_safe_font('DejaVu', '', 11)
                    
                elif line.startswith('- ') or line.startswith('* '):
                    # Listy punktowane
                    bullet = chr(149) if font_loaded else "-"
                    pdf.set_x(15)
                    # Tu też używamy nowej funkcji do formatowania treści punktu
                    pdf.write(5, bullet + " ")
                    print_formatted_text(line[2:])
                    
                else:
                    # Zwykły akapit z obsługą BOLD (**)
                    print_formatted_text(line)
            if citations:
                pdf.add_page()
                set_safe_font('DejaVu', 'B', 14)
                pdf.cell(0, 10, "Sources", 0, 1)
                set_safe_font('DejaVu', '', 10)
                
                for i, link in enumerate(citations, 1):
                    clean_link = ReportGenerator.clean_text(link)
                    if not font_loaded:
                        clean_link = clean_link.encode('latin-1', 'ignore').decode('latin-1')
                    
                    # Użycie write() zamiast multi_cell() dla płynnego zawijania
                    pdf.write(6, f"[{i}] {clean_link}")
                    pdf.ln(8) # Odstęp po każdym linku

            # fpdf2 returns bytearray directly, no need to encode
            return bytes(pdf.output())

# --- MAIN APPLICATION LOGIC ---
def main():
    st.title("🧩 fin.sankey | Financial Flow Visualizer")
    st.markdown("Cash flow visualization for NASDAQ/S&P500 companies")

    # --- STATE MANAGEMENT (SESSION STATE) ---
    # 1. State for Main Ticker
    if 'rev_change' not in st.session_state: st.session_state['rev_change'] = 0
    if 'cost_change' not in st.session_state: st.session_state['cost_change'] = 0
    
    # 2. State for Benchmark (Competitor)
    if 'comp_rev_change' not in st.session_state: st.session_state['comp_rev_change'] = 0
    if 'comp_cost_change' not in st.session_state: st.session_state['comp_cost_change'] = 0

    # Reset callbacks
    def reset_main_sliders():
        st.session_state['rev_change'] = 0
        st.session_state['cost_change'] = 0

    def reset_comp_sliders():
        st.session_state['comp_rev_change'] = 0
        st.session_state['comp_cost_change'] = 0

    # --- SIDEBAR ---
    with st.sidebar:
        # --- USER AUTH SECTION ---
        if SupabaseAuth.is_configured():
            # Initialize session state for auth
            if "user" not in st.session_state:
                st.session_state["user"] = None
            if "auth_mode" not in st.session_state:
                st.session_state["auth_mode"] = "login"  # or "register"

            # Restore Supabase session on each run
            SupabaseAuth.restore_session()

            current_user = st.session_state.get("user")

            if current_user:
                # User is logged in
                st.success(f"Welcome, {current_user.email}!")
                if st.button("Logout", use_container_width=True):
                    SupabaseAuth.sign_out()
                    st.session_state["user"] = None
                    st.rerun()

                # Show user stats
                watchlist = SupabaseAuth.get_watchlist(current_user.id)
                saved = SupabaseAuth.get_saved_analyses(current_user.id)
                st.caption(f"Watchlist: {len(watchlist)} | Saved analyses: {len(saved)}")
                st.markdown("---")
            else:
                # Login/Register forms
                auth_tab1, auth_tab2 = st.tabs(["Login", "Register"])

                with auth_tab1:
                    with st.form("login_form"):
                        login_email = st.text_input("Email", key="login_email")
                        login_password = st.text_input("Password", type="password", key="login_pass")
                        login_submit = st.form_submit_button("Login", use_container_width=True)

                        if login_submit:
                            if login_email and login_password:
                                result = SupabaseAuth.sign_in(login_email, login_password)
                                if result.get("success"):
                                    st.session_state["user"] = result["user"]
                                    st.success("Logged in successfully!")
                                    st.rerun()
                                else:
                                    st.error(result.get("error", "Login failed"))
                            else:
                                st.warning("Please enter email and password")

                with auth_tab2:
                    with st.form("register_form"):
                        reg_email = st.text_input("Email", key="reg_email")
                        reg_password = st.text_input("Password", type="password", key="reg_pass")
                        reg_password2 = st.text_input("Confirm Password", type="password", key="reg_pass2")
                        reg_submit = st.form_submit_button("Create Account", use_container_width=True)

                        if reg_submit:
                            if not reg_email or not reg_password:
                                st.warning("Please fill all fields")
                            elif reg_password != reg_password2:
                                st.error("Passwords don't match")
                            elif len(reg_password) < 6:
                                st.error("Password must be at least 6 characters")
                            else:
                                result = SupabaseAuth.sign_up(reg_email, reg_password)
                                if result.get("success"):
                                    st.success("Account created! Please check your email to confirm.")
                                else:
                                    st.error(result.get("error", "Registration failed"))

                st.markdown("---")

        st.header("Configuration")
        
        # Get ticker list
        tickers_list = DataManager.get_tickers_list()
        
        # --- MAIN SECTION ---
        st.subheader("1. Main Company")

        # Show user's watchlist if logged in
        current_user = st.session_state.get("user")
        if current_user and SupabaseAuth.is_configured():
            watchlist = SupabaseAuth.get_watchlist(current_user.id)
            if watchlist:
                watchlist_tickers = [f"{w['ticker']} | {w.get('company_name', '')}" for w in watchlist]
                st.caption("Your Watchlist:")
                selected_from_watchlist = st.selectbox(
                    "Quick select from watchlist:",
                    options=[""] + watchlist_tickers,
                    key="watchlist_select"
                )
                if selected_from_watchlist:
                    # Find matching item in tickers_list
                    ticker_from_wl = selected_from_watchlist.split(" | ")[0]
                    matching = [t for t in tickers_list if t.startswith(ticker_from_wl)]
                    if matching:
                        default_idx = tickers_list.index(matching[0])
                    else:
                        default_idx = 0
                else:
                    default_idx = 0
            else:
                default_idx = 0
        else:
            default_idx = 0

        selected_item = st.selectbox(
            "Search for a company:",
            options=tickers_list,
            index=default_idx
        )
        ticker_input = selected_item.split(" | ")[0]
        company_name = selected_item.split(" | ")[1] if " | " in selected_item else ticker_input

        # Add to watchlist button (if logged in)
        if current_user and SupabaseAuth.is_configured():
            user_watchlist_tickers = [w['ticker'] for w in SupabaseAuth.get_watchlist(current_user.id)]
            watchlist_limit = SupabaseAuth.can_add_to_watchlist(current_user.id)

            if ticker_input in user_watchlist_tickers:
                if st.button("Remove from Watchlist", key="remove_wl"):
                    if SupabaseAuth.remove_from_watchlist(current_user.id, ticker_input):
                        st.success(f"Removed {ticker_input} from watchlist!")
                        st.rerun()
                    else:
                        st.error("Failed to remove from watchlist")
            else:
                # Check watchlist limit
                can_add = watchlist_limit.get('allowed', True)
                if not can_add:
                    st.warning(f"⚠️ {watchlist_limit.get('message', 'Watchlist full')}")

                if st.button("Add to Watchlist", key="add_wl", disabled=not can_add):
                    result = SupabaseAuth.add_to_watchlist(current_user.id, ticker_input, company_name)
                    if result.get("success"):
                        st.success(f"Added {ticker_input} to watchlist!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result.get('error', 'Unknown error')}")

        # What-If for Main
        st.caption(f"Simulation: {ticker_input}")
        rev_change = st.slider("Revenue Change (%)", -30, 30, key='rev_change')
        cost_change = st.slider("Cost Change (%)", -30, 30, key='cost_change')
        st.button("↺ Reset (Main)", on_click=reset_main_sliders)
        
        st.markdown("---")
        
        # --- BENCHMARK SECTION ---
        st.subheader("2. Benchmark (Competitor)")
        enable_benchmark = st.checkbox("Compare with Competitor")
        ticker_comp = None
        
        # Initialize competitor variables to 0 to prevent crashes
        comp_rev_change = 0
        comp_cost_change = 0
        
        if enable_benchmark:
            selected_comp = st.selectbox(
                "Select Competitor:",
                options=tickers_list,
                index=1 if len(tickers_list) > 1 else 0,
                key="benchmark_select"
            )
            ticker_comp = selected_comp.split(" | ")[0]
            
            # What-If for Competitor
            st.caption(f"Simulation: {ticker_comp}")
            comp_rev_change = st.slider("Rev Change (Comp) %", -30, 30, key='comp_rev_change')
            comp_cost_change = st.slider("Cost Change (Comp) %", -30, 30, key='comp_cost_change')
            st.button("↺ Reset (Benchmark)", on_click=reset_comp_sliders)

    if not ticker_input:
        st.info("Select a company from the list to start.")
        return

    # Fetch data for main ticker
    data_mgr = DataManager()
    data_dict = data_mgr.get_financials(ticker_input)

    if not data_dict:
        return

    # --- PERIOD SELECTION (after data is loaded) ---
    # Get available periods for dropdown
    available_periods = DataManager.get_available_periods(data_dict['income_stmt'])

    # Check historical periods limit based on user tier
    current_user_periods = st.session_state.get("user")
    periods_limit = None  # None = unlimited
    is_guest = False

    if current_user_periods and SupabaseAuth.is_configured():
        periods_limit = SupabaseAuth.get_historical_periods_limit(current_user_periods.id)
    else:
        # Guest users get Free tier limits
        is_guest = True
        periods_limit = SupabaseAuth.TIER_LIMITS['free']['historical_periods']

    # Apply limit to available periods if needed
    if periods_limit is not None and available_periods and len(available_periods) > periods_limit:
        limited_periods = available_periods[:periods_limit]
        periods_limited = True
    else:
        limited_periods = available_periods
        periods_limited = False

    # Add period selector to sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("3. Reporting Period")
        if limited_periods:
            period_options = [p[0] for p in limited_periods]
            selected_period_name = st.selectbox(
                "Select period for analysis:",
                options=period_options,
                index=0,
                help="Choose which quarterly report to analyze"
            )
            # Find the index for the selected period
            selected_period_index = next(
                (p[1] for p in limited_periods if p[0] == selected_period_name), 0
            )
            # Show upgrade hint if periods are limited
            if periods_limited:
                if is_guest:
                    st.caption(f"🔒 Guest: {periods_limit} periods. Login for more.")
                else:
                    st.caption(f"🔒 Free tier: {periods_limit} periods. Upgrade for more.")
        else:
            selected_period_index = 0
            st.info("No historical periods available")

    # Process data for MAIN (with selected period and sliders)
    sankey_vals = data_mgr.extract_sankey_data(
        data_dict['income_stmt'],
        period_index=selected_period_index,
        revenue_mod=1 + (rev_change/100),
        cost_mod=1 + (cost_change/100)
    )

    # --- MAIN TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Viz & Benchmark", "📈 Metrics Dashboard", "🤖 AI Report", "📑 Extra Data"])

    with tab1:
        # Layout logic: Check if benchmark mode is on
        show_benchmark = enable_benchmark and ticker_comp
        
        if show_benchmark:
            # If benchmark active -> split screen
            col1, col2 = st.columns(2)
        else:
            # If benchmark off -> full width container
            col1 = st.container()
            col2 = None

        # DRAW MAIN CHART (Always in col1)
        with col1:
            st.subheader(f"Analysis: {ticker_input}")
            
            # --- ADDED SAFETY CHECK ---
            if sankey_vals.get('Revenue', 0) <= 0 and sankey_vals.get('OpEx_Total', 0) <= 0:
                st.warning(f"⚠️ Company {ticker_input} reports no revenue or significant costs (likely SPAC or holding). Sankey chart cannot be generated.")
            else:
                # Old code drawing charts
                if rev_change != 0 or cost_change != 0:
                    st.caption(f"Simulation: Rev {rev_change:+}%, Cost {cost_change:+}%")
                    
                fig_sankey = Visualizer.plot_sankey(sankey_vals, title_suffix=f"({ticker_input})")
                st.plotly_chart(fig_sankey, use_container_width=True, key="sankey_main")
                
                fig_water = Visualizer.plot_waterfall(sankey_vals, title_suffix=f"({ticker_input})")
                st.plotly_chart(fig_water, use_container_width=True, key="water_main")

        # DRAW BENCHMARK (Only if show_benchmark is True)
        if show_benchmark:
            with col2:
                st.subheader(f"Benchmark: {ticker_comp}")
                comp_data = data_mgr.get_financials(ticker_comp)

                if comp_data:
                    if comp_rev_change != 0 or comp_cost_change != 0:
                        st.caption(f"Simulation: Rev {comp_rev_change:+}%, Cost {comp_cost_change:+}%")

                    comp_vals = data_mgr.extract_sankey_data(
                        comp_data['income_stmt'],
                        revenue_mod=1 + (comp_rev_change/100),
                        cost_mod=1 + (comp_cost_change/100)
                    )

                    fig_sankey_comp = Visualizer.plot_sankey(comp_vals, title_suffix=f"({ticker_comp})")
                    st.plotly_chart(fig_sankey_comp, use_container_width=True, key="sankey_comp")

                    fig_water_comp = Visualizer.plot_waterfall(comp_vals, title_suffix=f"({ticker_comp})")
                    st.plotly_chart(fig_water_comp, use_container_width=True, key="water_comp")
                else:
                    st.warning("No data found for the comparison ticker.")

        # --- HISTORICAL TRENDS SECTION ---
        st.divider()
        st.subheader("📈 Historical Trends")

        # Plot historical trend chart
        fig_trend = Visualizer.plot_historical_trend(data_dict['income_stmt'])
        st.plotly_chart(fig_trend, use_container_width=True, key="historical_trend")

        # YoY metrics table
        yoy_metrics = Visualizer.calculate_yoy_metrics(data_dict['income_stmt'])
        if yoy_metrics:
            st.markdown("#### Year-over-Year Changes")
            yoy_cols = st.columns(len(yoy_metrics))
            for i, (metric_name, (current_val, yoy_change)) in enumerate(yoy_metrics.items()):
                with yoy_cols[i]:
                    # Format current value (handle negative values properly)
                    abs_val = abs(current_val)
                    sign = "-" if current_val < 0 else ""

                    if abs_val >= 1e9:
                        formatted_val = f"{sign}${abs_val/1e9:.1f}B"
                    elif abs_val >= 1e6:
                        formatted_val = f"{sign}${abs_val/1e6:.0f}M"
                    elif abs_val >= 1e3:
                        formatted_val = f"{sign}${abs_val/1e3:.0f}K"
                    else:
                        formatted_val = f"{sign}${abs_val:,.0f}"

                    # Format YoY change with color indicator
                    if yoy_change is not None:
                        delta_str = f"{yoy_change:+.1f}%"
                    else:
                        delta_str = None

                    st.metric(
                        label=metric_name,
                        value=formatted_val,
                        delta=delta_str
                    )

    with tab2:
        st.subheader("📊 Metrics Dashboard")
        
        # --- Data Preparation ---
        info = data_dict.get("info", {}) or {}
        bs = data_dict.get("balance_sheet", None)
        
        # Helper Formatters
        def fmt_num(val, suffix="", compact=False):
            if val is None: return "N/A"
            try:
                val = float(val)
                # Jeśli flaga compact=True, skracamy duże liczby
                if compact:
                    if val >= 1e12: return f"{val/1e12:.2f}T{suffix}"
                    if val >= 1e9: return f"{val/1e9:.2f}B{suffix}"
                    if val >= 1e6: return f"{val/1e6:.2f}M{suffix}"
                # Domyślne formatowanie dla mniejszych wskaźników (np. EPS, P/E)
                return f"{val:,.2f}{suffix}"
            except: return "N/A"

        def fmt_pct(val):
            if val is None: return "N/A"
            try: return f"{float(val)*100:.2f}%"
            except: return "N/A"
            
        def safe_div(a, b):
            try:
                return float(a) / float(b) if b else None
            except: return None

        # Calculations for custom metrics
        total_assets = None
        total_equity = None
        total_debt_bs = None
        cash = None

        if bs is not None and not bs.empty:
            # Try finding Total Assets
            for k in ["Total Assets", "Total assets"]:
                if k in bs.index:
                    total_assets = float(bs.loc[k].iloc[0])
                    break
            # Try finding Total Equity
            for k in ["Total Stockholder Equity", "Total Equity", "Stockholders Equity", "Stockholders' Equity"]:
                if k in bs.index:
                    total_equity = float(bs.loc[k].iloc[0])
                    break
            # Try finding Total Debt from balance sheet
            for k in ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"]:
                if k in bs.index:
                    total_debt_bs = float(bs.loc[k].iloc[0])
                    break
            # Try finding Cash
            for k in ["Cash And Cash Equivalents", "Cash", "Cash Cash Equivalents And Short Term Investments"]:
                if k in bs.index:
                    cash = float(bs.loc[k].iloc[0])
                    break

        # --- ROIC Calculation ---
        # ROIC = NOPAT / Invested Capital
        # NOPAT = Operating Income × (1 - Tax Rate)
        # Invested Capital = Total Equity + Total Debt - Cash
        roic = None
        income_stmt = data_dict.get("income_stmt")

        if income_stmt is not None and not income_stmt.empty:
            # Get Operating Income
            operating_income = None
            for k in ["Operating Income", "EBIT"]:
                if k in income_stmt.index:
                    operating_income = float(income_stmt.loc[k].iloc[0])
                    break

            # Calculate effective tax rate
            tax_rate = None
            pretax_income = None
            tax_provision = None

            for k in ["Pretax Income", "Income Before Tax"]:
                if k in income_stmt.index:
                    pretax_income = float(income_stmt.loc[k].iloc[0])
                    break

            for k in ["Tax Provision", "Income Tax Expense"]:
                if k in income_stmt.index:
                    tax_provision = float(income_stmt.loc[k].iloc[0])
                    break

            if pretax_income and pretax_income != 0 and tax_provision is not None:
                tax_rate = tax_provision / pretax_income
                # Clamp tax rate to reasonable range (0-50%)
                tax_rate = max(0, min(0.5, tax_rate))
            else:
                tax_rate = 0.21  # Default US corporate tax rate

            # Calculate NOPAT
            if operating_income is not None:
                nopat = operating_income * (1 - tax_rate)

                # Calculate Invested Capital
                # Use debt from info if balance sheet debt not available
                total_debt_val = total_debt_bs if total_debt_bs else info.get("totalDebt", 0) or 0
                equity_val = total_equity or 0
                cash_val = cash or 0

                invested_capital = equity_val + total_debt_val - cash_val

                if invested_capital and invested_capital > 0:
                    roic = nopat / invested_capital

        shares = info.get("sharesOutstanding")
        debt = info.get("totalDebt")
        rev = info.get("totalRevenue")
        empl = info.get("fullTimeEmployees")
        
        assets_per_share = safe_div(total_assets, shares)
        debt_to_assets = safe_div(debt, total_assets)
        debt_to_capital = safe_div(debt, (debt + total_equity) if (debt and total_equity) else None)
        rev_per_empl = safe_div(rev, empl)

        # --- CSS STYLING FOR CARDS ---
        st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: #262730;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #464b5c;
        }
        </style>
        """, unsafe_allow_html=True)

        # ==============================================================================
        # SECTION 1: KEY HIGHLIGHTS
        # ==============================================================================
        st.markdown("#### 🔹 Key Highlights")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Revenue per Share", fmt_num(info.get("revenuePerShare")))
        k2.metric("EPS (Trailing)", fmt_num(info.get("trailingEps")))
        k3.metric("ROE", fmt_pct(info.get("returnOnEquity")))
        k4.metric("ROIC", fmt_pct(roic), help="Return on Invested Capital = NOPAT / (Equity + Debt - Cash)") 

        k1b, k2b, k3b, k4b = st.columns(4)
        k1b.metric("Debt / Equity", fmt_num(info.get("debtToEquity")))
        k2b.metric("Book Value / Share", fmt_num(info.get("bookValue")))
        k3b.metric("Current Ratio", fmt_num(info.get("currentRatio")))
        k4b.metric("Quick Ratio", fmt_num(info.get("quickRatio")))

        st.divider()

        # ==============================================================================
        # SECTION 2: VALUATION
        # ==============================================================================
        st.markdown("#### 💲 Valuation")
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Price / Sales (P/S)", fmt_num(info.get("priceToSalesTrailing12Months")))
        w2.metric("Price / Earnings (P/E)", fmt_num(info.get("trailingPE")))
        w3.metric("Price / Book (P/B)", fmt_num(info.get("priceToBook")))
        w4.metric("PEG Ratio", fmt_num(info.get("pegRatio")))

        w1b, w2b, w3b, w4b = st.columns(4)
        w1b.metric("EV / Revenue", fmt_num(info.get("enterpriseToRevenue")))
        w2b.metric("EV / EBITDA", fmt_num(info.get("enterpriseToEbitda")))
        w3b.metric("Market Cap", fmt_num(info.get("marketCap"), suffix=" $", compact=True))
        w4b.metric("Forward P/E", fmt_num(info.get("forwardPE")))

        st.divider()

        # ==============================================================================
        # SECTION 3: FINANCIAL HEALTH (SOLVENCY)
        # ==============================================================================
        st.markdown("#### 🏦 Financial Health")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Total Assets / Share", fmt_num(assets_per_share))
        f2.metric("Debt / Assets", fmt_num(debt_to_assets))
        f3.metric("Debt / Total Capital", fmt_num(debt_to_capital))
        f4.metric("Revenue / Employee", fmt_num(rev_per_empl))
        
        st.divider()

        # ==============================================================================
        # SECTION 4: PROFITABILITY
        # ==============================================================================
        st.markdown("#### 📈 Profitability")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Gross Margin", fmt_pct(info.get("grossMargins")))
        r2.metric("Operating Margin", fmt_pct(info.get("operatingMargins")))
        r3.metric("Profit Margin", fmt_pct(info.get("profitMargins")))
        r4.metric("Beta (Volatility)", fmt_num(info.get("beta")))

    with tab3:
        st.header("🤖 AI Report (Perplexity Sonar)")
        st.caption("This analysis combines fundamental data with the latest web news (Live Search).")

        # --- KONFIGURACJA API (BEZPIECZNE POBIERANIE) ---
        # Priorytet: 1) Streamlit secrets, 2) Zmienna środowiskowa
        PERPLEXITY_API_KEY = None

        # Próba pobrania z st.secrets (Streamlit Cloud / lokalny secrets.toml)
        try:
            if "PERPLEXITY_API_KEY" in st.secrets:
                PERPLEXITY_API_KEY = st.secrets["PERPLEXITY_API_KEY"]
        except Exception:
            pass

        # Fallback: zmienna środowiskowa (lokalne uruchomienie)
        if not PERPLEXITY_API_KEY:
            PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")

        # Sprawdzenie czy klucz jest dostępny
        api_key_ready = PERPLEXITY_API_KEY and len(PERPLEXITY_API_KEY) >= 10

        # Sprawdzenie czy mamy dane finansowe
        if not sankey_vals:
            st.warning("Insufficient financial data to generate the report.")
        elif not api_key_ready:
            st.error("AI Reports are currently unavailable. Please contact the administrator.")
        else:
            # Generowanie Promptu (teraz ukryte dla użytkownika)
            prompt = ReportGenerator.generate_ai_prompt(ticker_input, sankey_vals, data_dict['info'])

            # --- SPRAWDZENIE CACHE (PRIORYTET: Global Supabase -> User Saved -> Local File) ---
            current_user = st.session_state.get("user")
            user_id = current_user.id if current_user else None

            # 1. Check Supabase caches (global + user saved)
            supabase_cached = None
            if SupabaseAuth.is_configured():
                supabase_cached = SupabaseAuth.get_best_cached_report(ticker_input, user_id)

            # 2. Check local file cache as fallback
            local_cached, local_cache_age = ReportGenerator.get_cached_report(ticker_input)

            # Determine best cache source
            cached_report = None
            cache_source = None

            if supabase_cached:
                cached_report = supabase_cached
                cache_source = supabase_cached.get("from_cache", "global")
                if cache_source == "global":
                    age_info = f"{supabase_cached.get('age_days', 0)} days old"
                else:
                    age_info = "from your saved analyses"
            elif local_cached:
                cached_report = local_cached
                cache_source = "local"
                cache_hours = int(local_cache_age)
                cache_minutes = int((local_cache_age - cache_hours) * 60)
                age_info = f"{cache_hours}h {cache_minutes}m old"

            # --- CHECK AI REPORT LIMIT ---
            ai_limit_info = None
            can_generate = True
            guest_blocked = False

            if not current_user:
                # Guest users cannot generate AI reports
                can_generate = False
                guest_blocked = True
                st.warning("🔒 Login required to generate AI reports. Create a free account to get started!")
            elif SupabaseAuth.is_configured():
                ai_limit_info = SupabaseAuth.can_generate_ai_report(current_user.id)
                can_generate = ai_limit_info.get('allowed', True)

                # Show usage info
                used = ai_limit_info.get('used', 0)
                limit = ai_limit_info.get('limit')
                tier = ai_limit_info.get('tier', 'free')

                if limit is not None:
                    remaining = limit - used
                    if remaining > 0:
                        st.caption(f"📊 AI Reports: {used}/{limit} used this month ({tier.upper()} tier)")
                    else:
                        st.warning(f"⚠️ {ai_limit_info.get('message', 'Limit reached')}")
                else:
                    st.caption(f"📊 AI Reports: Unlimited ({tier.upper()} tier)")

            # Wyświetlenie informacji o cache
            if cached_report:
                if cache_source == "global":
                    st.info(f"🌐 Global cached report available ({age_info}) - saves API costs!")
                elif cache_source == "user_saved":
                    st.info(f"👤 Found in your saved analyses")
                else:
                    st.info(f"💾 Local cached report available ({age_info})")

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    use_cache_btn = st.button("📂 Load Cached Report", type="secondary")
                with btn_col2:
                    generate_btn = st.button("🚀 Generate New Report", type="primary", disabled=not can_generate)
            else:
                generate_btn = st.button("🚀 Generate Live Report", type="primary", disabled=not can_generate)
                use_cache_btn = False

            # Session State
            if "ai_report_content" not in st.session_state:
                st.session_state["ai_report_content"] = None

            # --- LOGIKA CACHE ---
            if use_cache_btn and cached_report:
                # Clean cached text in case it contains old unclean data
                if cached_report.get("text"):
                    cached_report["text"] = ReportGenerator.clean_text(cached_report["text"])
                st.session_state["ai_report_data"] = cached_report
                st.toast(f"✅ Loaded from {cache_source} cache!", icon="💾")

            # --- LOGIKA PRZYCISKU GENEROWANIA ---
            if generate_btn:
                with st.spinner("⏳ Perplexity is searching the web and analyzing data..."):
                        # Wywołanie API (zwraca teraz krotkę: tekst, lista_cytowań)
                        analysis_text, citations = ReportGenerator.get_ai_analysis(PERPLEXITY_API_KEY, prompt)

                        # CZYŚĆ TEKST OD RAZU po otrzymaniu z API
                        analysis_text = ReportGenerator.clean_text(analysis_text)

                        # Zapisanie wyniku do sesji jako słownik
                        report_data = {
                            "text": analysis_text,
                            "citations": citations
                        }
                        st.session_state["ai_report_data"] = report_data

                        # Zapisz do LOCAL cache
                        ReportGenerator.save_report_to_cache(ticker_input, report_data)

                        # Zapisz do GLOBAL Supabase cache (jeśli zalogowany)
                        if current_user and SupabaseAuth.is_configured():
                            financial_snapshot = {
                                "revenue": sankey_vals.get('Revenue', 0),
                                "net_income": sankey_vals.get('Net Income', 0),
                                "pe_ratio": info.get("trailingPE")
                            }
                            if SupabaseAuth.save_to_global_cache(ticker_input, analysis_text, citations, financial_snapshot):
                                st.toast("✅ Report saved to global cache!", icon="🌐")
                            else:
                                st.toast("✅ Report saved locally", icon="💾")

                            # INCREMENT AI REPORT USAGE COUNTER
                            SupabaseAuth.increment_ai_report_usage(current_user.id)
            
            # --- WYŚWIETLANIE WYNIKU (JEŚLI ISTNIEJE W SESJI) ---
            if "ai_report_data" in st.session_state and st.session_state["ai_report_data"]:
                report_data = st.session_state["ai_report_data"]

                # Clean the text before display (remove zero-width chars, fix formatting)
                display_text = ReportGenerator.clean_text(report_data["text"]) if report_data.get("text") else ""

                # Escape $ signs to prevent LaTeX interpretation in Streamlit markdown
                display_text = display_text.replace("$", "\\$")

                st.markdown("### 📝 Analysis Result")
                st.markdown(display_text)
                
                # Wyświetlenie listy źródeł (jeśli są dostępne)
                if report_data["citations"]:
                    st.divider()
                    st.markdown("#### 📚 Sources / Citations")
                    for i, link in enumerate(report_data["citations"], 1):
                        st.markdown(f"**[{i}]** [{link}]({link})")
                
                st.divider()
                
                # Przygotowanie danych do PDF
                rev = sankey_vals.get('Revenue', 1)
                net = sankey_vals.get('Net Income', 0)
                metrics_for_pdf = {
                    "Ticker": ticker_input,
                    "P/E Ratio": str(info.get("trailingPE", "N/A")),
                    "Revenue": f"${rev:,.0f}",
                    "Net Income": f"${net:,.0f}"
                }
                
                # Generowanie pliku PDF (przekazujemy też cytowania)
                pdf_bytes = ReportGenerator.create_pdf(
                    ticker_input, 
                    report_data["text"], # Nie usuwamy gwiazdek markdown, bo nowa klasa PDF je obsłuży
                    metrics_for_pdf,
                    citations=report_data["citations"]
                )
                
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    # Check export permission for PDF
                    current_user_for_export = st.session_state.get("user")
                    can_export_pdf = False
                    is_guest_export = False

                    if current_user_for_export and SupabaseAuth.is_configured():
                        export_info = SupabaseAuth.can_export(current_user_for_export.id)
                        can_export_pdf = export_info.get('allowed', True)
                    else:
                        # Guest users get Free tier limits (no export)
                        is_guest_export = True
                        can_export_pdf = SupabaseAuth.TIER_LIMITS['free']['export_enabled']

                    if can_export_pdf:
                        st.download_button(
                            label="📄 Download PDF Report",
                            data=pdf_bytes,
                            file_name=f"{ticker_input}_Perplexity_Report.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.button("📄 Download PDF Report", disabled=True, use_container_width=True)
                        if is_guest_export:
                            st.caption("🔒 Login & upgrade to Pro to export PDFs")
                        else:
                            st.caption("🔒 Upgrade to Pro to export PDFs")
                with dl_col2:
                    # Save to account (if logged in)
                    current_user = st.session_state.get("user")
                    if current_user and SupabaseAuth.is_configured():
                        # Check saved analyses limit
                        save_limit = SupabaseAuth.can_save_analysis(current_user.id)
                        can_save = save_limit.get('allowed', True)

                        if not can_save:
                            st.warning(f"⚠️ {save_limit.get('message', 'Limit reached')}")

                        if st.button("💾 Save to My Analyses", use_container_width=True, key="save_analysis", disabled=not can_save):
                            financial_data = {
                                "revenue": sankey_vals.get('Revenue', 0),
                                "net_income": sankey_vals.get('Net Income', 0),
                                "pe_ratio": info.get("trailingPE"),
                            }
                            if SupabaseAuth.save_analysis(
                                current_user.id,
                                ticker_input,
                                report_data["text"],
                                report_data.get("citations"),
                                financial_data
                            ):
                                st.success("Analysis saved to your account!")
                            else:
                                st.error("Failed to save analysis")
                    else:
                        st.info("Login to save analyses to your account")

    with tab4:
        st.header("Additional Data")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Insider Trading")
            insider_df = data_dict['insider']
            if not insider_df.empty:
                st.dataframe(insider_df, use_container_width=True)
            else:
                st.write("No insider trading data available.") 
        with col_b:
            st.subheader("Analyst Sentiment")
            rec_df = data_dict['recommendations']
            if not rec_df.empty:
                # Display sentiment chart
                sentiment_fig = Visualizer.plot_sentiment(rec_df)
                if sentiment_fig:
                    st.plotly_chart(sentiment_fig, use_container_width=True)
                # Display recent recommendations table
                st.dataframe(rec_df.tail(10), use_container_width=True)
            else:
                st.write("No analyst recommendations available.")

        # --- EXPORT DATA SECTION ---
        st.divider()
        st.subheader("📥 Export Financial Data")

        # Check export permission for Excel
        current_user_excel = st.session_state.get("user")
        can_export_excel = False
        is_guest_excel = False

        if current_user_excel and SupabaseAuth.is_configured():
            export_info_excel = SupabaseAuth.can_export(current_user_excel.id)
            can_export_excel = export_info_excel.get('allowed', True)
        else:
            # Guest users get Free tier limits (no export)
            is_guest_excel = True
            can_export_excel = SupabaseAuth.TIER_LIMITS['free']['export_enabled']

        if can_export_excel:
            st.write("Download raw financial data for further analysis in Excel.")
        else:
            if is_guest_excel:
                st.warning("🔒 Excel export requires Pro tier. Login & upgrade to export data.")
            else:
                st.warning("🔒 Excel export is available for Pro and Enterprise tiers. Upgrade to export data.")

        export_col1, export_col2, export_col3 = st.columns(3)

        income_stmt = data_dict['income_stmt']
        balance_sheet = data_dict['balance_sheet']

        with export_col1:
            if not can_export_excel:
                st.button("📊 Income Statement", disabled=True, help="Upgrade to Pro to export")
            elif income_stmt is not None and not income_stmt.empty:
                income_excel = convert_df_to_excel(income_stmt.T, "Income Statement")
                st.download_button(
                    label="📊 Income Statement",
                    data=income_excel,
                    file_name=f"{ticker_input}_income_statement.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download full income statement data"
                )
            else:
                st.button("📊 Income Statement", disabled=True, help="No data available")

        with export_col2:
            if not can_export_excel:
                st.button("📋 Balance Sheet", disabled=True, help="Upgrade to Pro to export")
            elif balance_sheet is not None and not balance_sheet.empty:
                balance_excel = convert_df_to_excel(balance_sheet.T, "Balance Sheet")
                st.download_button(
                    label="📋 Balance Sheet",
                    data=balance_excel,
                    file_name=f"{ticker_input}_balance_sheet.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download full balance sheet data"
                )
            else:
                st.button("📋 Balance Sheet", disabled=True, help="No data available")

        with export_col3:
            if not can_export_excel:
                st.button("📦 All Data (Multi-sheet)", disabled=True, help="Upgrade to Pro to export")
            else:
                # Export all data in one file with multiple sheets
                all_data = {
                    "Income Statement": income_stmt.T if income_stmt is not None and not income_stmt.empty else pd.DataFrame(),
                    "Balance Sheet": balance_sheet.T if balance_sheet is not None and not balance_sheet.empty else pd.DataFrame(),
                    "Insider Trading": insider_df if not insider_df.empty else pd.DataFrame(),
                    "Recommendations": rec_df if not rec_df.empty else pd.DataFrame()
                }
                # Filter out empty dataframes
                all_data = {k: v for k, v in all_data.items() if not v.empty}

                if all_data:
                    all_excel = convert_multiple_df_to_excel(all_data)
                    st.download_button(
                        label="📦 All Data (Multi-sheet)",
                        data=all_excel,
                        file_name=f"{ticker_input}_all_financial_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download all available data in one Excel file"
                )
            else:
                st.button("📦 All Data", disabled=True, help="No data available")

        # --- MY SAVED ANALYSES SECTION (for logged-in users) ---
        current_user = st.session_state.get("user")
        if current_user and SupabaseAuth.is_configured():
            st.divider()
            st.subheader("📁 My Saved Analyses")

            saved_analyses = SupabaseAuth.get_saved_analyses(current_user.id)

            if saved_analyses:
                for analysis in saved_analyses:
                    with st.expander(f"**{analysis['ticker']}** - {analysis['created_at'][:10]}"):
                        st.markdown(analysis.get('report_text', 'No content')[:500] + "...")

                        if analysis.get('financial_data'):
                            fd = analysis['financial_data']
                            st.caption(f"Revenue: ${fd.get('revenue', 0):,.0f} | Net Income: ${fd.get('net_income', 0):,.0f}")

                        col_view, col_del = st.columns([3, 1])
                        with col_del:
                            if st.button("Delete", key=f"del_{analysis['id']}"):
                                if SupabaseAuth.delete_analysis(current_user.id, analysis['id']):
                                    st.success("Analysis deleted!")
                                    st.rerun()
            else:
                st.info("No saved analyses yet. Generate an AI report and click 'Save to My Analyses' to save it here.")

if __name__ == "__main__":
     main()
