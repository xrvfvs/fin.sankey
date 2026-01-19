# -*- coding: utf-8 -*-
"""
Supabase authentication and user data management module.
"""

import datetime
import streamlit as st
from supabase import create_client, Client

from config import TIER_LIMITS, GLOBAL_CACHE_TTL_DAYS, get_tier_limits


class SupabaseAuth:
    """Helper class for Supabase authentication and user data management."""

    _client = None

    # Reference to TIER_LIMITS from config for backwards compatibility
    TIER_LIMITS = TIER_LIMITS

    @classmethod
    def get_tier_limits(cls, tier: str) -> dict:
        """Get limits for a specific tier."""
        return get_tier_limits(tier)

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
                if age_days <= GLOBAL_CACHE_TTL_DAYS:
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
        except Exception:
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
