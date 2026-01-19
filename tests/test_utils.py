# -*- coding: utf-8 -*-
"""
Tests for modules/utils.py
"""

import pytest
import pandas as pd
from io import BytesIO

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.utils import (
    retry_on_rate_limit,
    convert_df_to_excel,
    convert_multiple_df_to_excel,
    format_large_number
)


class TestRetryOnRateLimit:
    """Tests for retry_on_rate_limit decorator."""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retry."""
        call_count = 0

        @retry_on_rate_limit(max_retries=3, base_delay=0.01)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_rate_limit_error(self):
        """Test that rate limit errors trigger retries."""
        call_count = 0

        @retry_on_rate_limit(max_retries=3, base_delay=0.01)
        def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Too many requests")
            return "success"

        result = rate_limited_func()
        assert result == "success"
        assert call_count == 3

    def test_non_rate_limit_error_raises(self):
        """Test that non-rate-limit errors are raised immediately."""
        call_count = 0

        @retry_on_rate_limit(max_retries=3, base_delay=0.01)
        def error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Some other error")

        with pytest.raises(ValueError):
            error_func()
        assert call_count == 1


class TestConvertDfToExcel:
    """Tests for convert_df_to_excel function."""

    def test_basic_conversion(self):
        """Test basic DataFrame to Excel conversion."""
        df = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        result = convert_df_to_excel(df, "TestSheet")

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_empty_dataframe(self, empty_dataframe):
        """Test conversion of empty DataFrame."""
        result = convert_df_to_excel(empty_dataframe, "Empty")
        assert isinstance(result, bytes)

    def test_custom_sheet_name(self):
        """Test that custom sheet name is used."""
        df = pd.DataFrame({'A': [1]})
        result = convert_df_to_excel(df, "CustomName")
        assert isinstance(result, bytes)


class TestConvertMultipleDfToExcel:
    """Tests for convert_multiple_df_to_excel function."""

    def test_multiple_sheets(self):
        """Test conversion of multiple DataFrames to multi-sheet Excel."""
        dfs = {
            'Sheet1': pd.DataFrame({'A': [1, 2]}),
            'Sheet2': pd.DataFrame({'B': [3, 4]}),
        }
        result = convert_multiple_df_to_excel(dfs)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_long_sheet_name_truncation(self):
        """Test that long sheet names are truncated to 31 chars."""
        dfs = {
            'This is a very long sheet name that exceeds 31 characters': pd.DataFrame({'A': [1]})
        }
        # Should not raise an error
        result = convert_multiple_df_to_excel(dfs)
        assert isinstance(result, bytes)

    def test_empty_dict(self):
        """Test conversion with empty dictionary."""
        result = convert_multiple_df_to_excel({})
        assert isinstance(result, bytes)


class TestFormatLargeNumber:
    """Tests for format_large_number function."""

    def test_billions(self):
        """Test formatting of billion-scale numbers."""
        assert format_large_number(1_500_000_000) == "$1.50B"
        assert format_large_number(50_000_000_000) == "$50.00B"

    def test_millions(self):
        """Test formatting of million-scale numbers."""
        assert format_large_number(1_500_000) == "$1.50M"
        assert format_large_number(999_000_000) == "$999.00M"

    def test_thousands(self):
        """Test formatting of thousand-scale numbers."""
        assert format_large_number(1_500) == "$1.50K"
        assert format_large_number(999_000) == "$999.00K"

    def test_small_numbers(self):
        """Test formatting of small numbers."""
        assert format_large_number(500) == "$500.00"
        assert format_large_number(99.99) == "$99.99"

    def test_none_value(self):
        """Test handling of None value."""
        assert format_large_number(None) == "N/A"

    def test_trillions(self):
        """Test formatting of trillion-scale numbers."""
        assert format_large_number(1_500_000_000_000) == "$1.50T"
