# -*- coding: utf-8 -*-
"""
Tests for modules/data_manager.py
"""

import pytest
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_manager import DataManager


class TestGetAvailablePeriods:
    """Tests for DataManager.get_available_periods method."""

    def test_returns_periods_list(self, sample_income_stmt):
        """Test that available periods are returned correctly."""
        periods = DataManager.get_available_periods(sample_income_stmt)

        assert isinstance(periods, list)
        assert len(periods) == 4
        # Each period should be a tuple (display_name, index)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in periods)

    def test_period_format(self, sample_income_stmt):
        """Test that period names are formatted correctly."""
        periods = DataManager.get_available_periods(sample_income_stmt)

        # First period should be Q3 2024
        assert "2024-Q3" in periods[0][0]
        assert periods[0][1] == 0

    def test_empty_dataframe(self, empty_dataframe):
        """Test handling of empty DataFrame."""
        periods = DataManager.get_available_periods(empty_dataframe)
        assert periods == []

    def test_none_input(self):
        """Test handling of None input."""
        periods = DataManager.get_available_periods(None)
        assert periods == []


class TestExtractSankeyData:
    """Tests for DataManager.extract_sankey_data method."""

    def test_extracts_all_fields(self, sample_income_stmt):
        """Test that all required fields are extracted."""
        data = DataManager.extract_sankey_data(sample_income_stmt)

        required_fields = [
            'Revenue', 'COGS', 'Gross Profit', 'OpEx_Total',
            'R&D', 'SG&A', 'Other OpEx', 'Operating Profit',
            'Taxes', 'Interest', 'Net Income'
        ]
        for field in required_fields:
            assert field in data

    def test_correct_values(self, sample_income_stmt):
        """Test that extracted values are correct."""
        data = DataManager.extract_sankey_data(sample_income_stmt, period_index=0)

        assert data['Revenue'] == 100_000_000_000
        assert data['COGS'] == 40_000_000_000
        assert data['Gross Profit'] == 60_000_000_000

    def test_revenue_modifier(self, sample_income_stmt):
        """Test revenue modifier works correctly."""
        data = DataManager.extract_sankey_data(
            sample_income_stmt,
            period_index=0,
            revenue_mod=1.1  # +10%
        )

        # Use pytest.approx for float comparison
        assert data['Revenue'] == pytest.approx(110_000_000_000, rel=1e-9)  # 100B * 1.1

    def test_cost_modifier(self, sample_income_stmt):
        """Test cost modifier works correctly."""
        data = DataManager.extract_sankey_data(
            sample_income_stmt,
            period_index=0,
            cost_mod=1.2  # +20%
        )

        assert data['COGS'] == 48_000_000_000  # 40B * 1.2

    def test_different_periods(self, sample_income_stmt):
        """Test extracting data from different periods."""
        data_q3 = DataManager.extract_sankey_data(sample_income_stmt, period_index=0)
        data_q2 = DataManager.extract_sankey_data(sample_income_stmt, period_index=1)

        assert data_q3['Revenue'] == 100_000_000_000
        assert data_q2['Revenue'] == 95_000_000_000

    def test_empty_dataframe(self, empty_dataframe):
        """Test handling of empty DataFrame."""
        data = DataManager.extract_sankey_data(empty_dataframe)
        assert data == {}

    def test_none_input(self):
        """Test handling of None input."""
        data = DataManager.extract_sankey_data(None)
        assert data == {}

    def test_invalid_period_index(self, sample_income_stmt):
        """Test handling of invalid period index (falls back to 0)."""
        data = DataManager.extract_sankey_data(sample_income_stmt, period_index=999)
        # Should fall back to period 0
        assert data['Revenue'] == 100_000_000_000

    def test_gross_profit_calculation(self, sample_income_stmt):
        """Test that Gross Profit = Revenue - COGS."""
        data = DataManager.extract_sankey_data(sample_income_stmt)
        assert data['Gross Profit'] == data['Revenue'] - data['COGS']

    def test_other_opex_non_negative(self, sample_income_stmt):
        """Test that Other OpEx is never negative."""
        data = DataManager.extract_sankey_data(sample_income_stmt)
        assert data['Other OpEx'] >= 0
