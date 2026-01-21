# -*- coding: utf-8 -*-
"""
Tests for config.py
"""

import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TIER_LIMITS, get_tier_limits


class TestTierLimits:
    """Tests for TIER_LIMITS configuration."""

    def test_all_tiers_defined(self):
        """Test that all tiers are defined."""
        assert 'free' in TIER_LIMITS
        assert 'pro' in TIER_LIMITS
        assert 'enterprise' in TIER_LIMITS

    def test_free_tier_has_limits(self):
        """Test that free tier has restrictions."""
        free = TIER_LIMITS['free']
        assert free['ai_reports_per_month'] == 3
        assert free['watchlist_max'] == 5
        assert free['saved_analyses_max'] == 5
        assert free['export_enabled'] is False
        assert free['historical_periods'] == 2

    def test_pro_tier_has_higher_limits(self):
        """Test that pro tier has higher limits than free."""
        free = TIER_LIMITS['free']
        pro = TIER_LIMITS['pro']

        assert pro['ai_reports_per_month'] > free['ai_reports_per_month']
        assert pro['watchlist_max'] > free['watchlist_max']
        assert pro['saved_analyses_max'] > free['saved_analyses_max']
        assert pro['export_enabled'] is True

    def test_enterprise_tier_unlimited(self):
        """Test that enterprise tier has unlimited access."""
        enterprise = TIER_LIMITS['enterprise']

        assert enterprise['ai_reports_per_month'] is None
        assert enterprise['watchlist_max'] is None
        assert enterprise['saved_analyses_max'] is None
        assert enterprise['export_enabled'] is True
        assert enterprise['historical_periods'] is None

    def test_all_tiers_have_same_keys(self):
        """Test that all tiers have the same configuration keys."""
        free_keys = set(TIER_LIMITS['free'].keys())
        pro_keys = set(TIER_LIMITS['pro'].keys())
        enterprise_keys = set(TIER_LIMITS['enterprise'].keys())

        assert free_keys == pro_keys == enterprise_keys


class TestGetTierLimits:
    """Tests for get_tier_limits function."""

    def test_get_free_tier(self):
        """Test getting free tier limits."""
        limits = get_tier_limits('free')
        assert limits == TIER_LIMITS['free']

    def test_get_pro_tier(self):
        """Test getting pro tier limits."""
        limits = get_tier_limits('pro')
        assert limits == TIER_LIMITS['pro']

    def test_get_enterprise_tier(self):
        """Test getting enterprise tier limits."""
        limits = get_tier_limits('enterprise')
        assert limits == TIER_LIMITS['enterprise']

    def test_unknown_tier_returns_free(self):
        """Test that unknown tier falls back to free."""
        limits = get_tier_limits('unknown_tier')
        assert limits == TIER_LIMITS['free']

    def test_empty_string_returns_free(self):
        """Test that empty string falls back to free."""
        limits = get_tier_limits('')
        assert limits == TIER_LIMITS['free']

    def test_case_sensitivity(self):
        """Test that tier names are case-sensitive."""
        # 'FREE' should not match 'free'
        limits = get_tier_limits('FREE')
        assert limits == TIER_LIMITS['free']  # Falls back to free
