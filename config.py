# -*- coding: utf-8 -*-
"""
Configuration constants and tier limits for the Financial Sankey application.
"""

# --- TIER LIMITS CONFIGURATION ---
TIER_LIMITS = {
    'free': {
        'ai_reports_per_month': 3,
        'watchlist_max': 5,
        'saved_analyses_max': 5,
        'export_enabled': False,
        'historical_periods': 2,  # Only last 2 periods
        'portfolio_max': 3,  # Max stocks in portfolio
    },
    'pro': {
        'ai_reports_per_month': 30,
        'watchlist_max': 25,
        'saved_analyses_max': 50,
        'export_enabled': True,
        'historical_periods': None,  # All periods
        'portfolio_max': 25,
    },
    'enterprise': {
        'ai_reports_per_month': None,  # Unlimited
        'watchlist_max': None,  # Unlimited
        'saved_analyses_max': None,  # Unlimited
        'export_enabled': True,
        'historical_periods': None,  # All periods
        'portfolio_max': None,  # Unlimited
    }
}

# --- APPLICATION SETTINGS ---
APP_TITLE = "Financial Sankey"
APP_ICON = ":material/monitoring:"
APP_LAYOUT = "wide"

# --- CACHE SETTINGS ---
LOCAL_CACHE_DIR = ".report_cache"
LOCAL_CACHE_TTL_HOURS = 24
GLOBAL_CACHE_TTL_DAYS = 7

# --- API SETTINGS ---
PERPLEXITY_MODEL = "sonar"
PERPLEXITY_MAX_TOKENS = 4000

# --- DEFAULT TICKERS FOR DEMO ---
DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]


def get_tier_limits(tier: str) -> dict:
    """Get limits for a specific tier."""
    return TIER_LIMITS.get(tier, TIER_LIMITS['free'])
