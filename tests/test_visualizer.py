# -*- coding: utf-8 -*-
"""
Tests for modules/visualizer.py
"""

import pytest
import pandas as pd
import plotly.graph_objects as go

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.visualizer import Visualizer


class TestFormatters:
    """Tests for Visualizer formatting methods."""

    def test_fmt_trillions(self):
        """Test formatting of trillion-scale numbers."""
        result = Visualizer._fmt(1_500_000_000_000)
        assert result == "$1.5T"

    def test_fmt_billions(self):
        """Test formatting of billion-scale numbers."""
        result = Visualizer._fmt(50_000_000_000)
        assert result == "$50.0B"

    def test_fmt_millions(self):
        """Test formatting of million-scale numbers."""
        result = Visualizer._fmt(5_000_000)
        assert result == "$5.0M"

    def test_fmt_small_numbers(self):
        """Test formatting of small numbers."""
        result = Visualizer._fmt(500)
        assert result == "$500"

    def test_format_financial_value_billions(self):
        """Test _format_financial_value for billions."""
        result = Visualizer._format_financial_value(2_500_000_000)
        assert result == "$2.5B"

    def test_format_financial_value_negative(self):
        """Test _format_financial_value for negative numbers."""
        result = Visualizer._format_financial_value(-1_000_000_000)
        assert result == "-$1.0B"

    def test_format_financial_value_none(self):
        """Test _format_financial_value for None."""
        result = Visualizer._format_financial_value(None)
        assert result == "N/A"


class TestPlotSankey:
    """Tests for Visualizer.plot_sankey method."""

    def test_returns_figure(self, sample_sankey_data):
        """Test that plot_sankey returns a Plotly Figure."""
        fig = Visualizer.plot_sankey(sample_sankey_data)
        assert isinstance(fig, go.Figure)

    def test_empty_data_returns_empty_figure(self):
        """Test that empty data returns empty Figure."""
        fig = Visualizer.plot_sankey({})
        assert isinstance(fig, go.Figure)

    def test_none_data_returns_empty_figure(self):
        """Test that None data returns empty Figure."""
        fig = Visualizer.plot_sankey(None)
        assert isinstance(fig, go.Figure)

    def test_figure_has_sankey_trace(self, sample_sankey_data):
        """Test that figure contains Sankey trace."""
        fig = Visualizer.plot_sankey(sample_sankey_data)
        assert len(fig.data) > 0
        assert isinstance(fig.data[0], go.Sankey)

    def test_title_suffix(self, sample_sankey_data):
        """Test that title suffix is applied."""
        fig = Visualizer.plot_sankey(sample_sankey_data, title_suffix="(AAPL)")
        assert "(AAPL)" in fig.layout.title.text


class TestPlotWaterfall:
    """Tests for Visualizer.plot_waterfall method."""

    def test_returns_figure(self, sample_sankey_data):
        """Test that plot_waterfall returns a Plotly Figure."""
        fig = Visualizer.plot_waterfall(sample_sankey_data)
        assert isinstance(fig, go.Figure)

    def test_empty_data_returns_empty_figure(self):
        """Test that empty data returns empty Figure."""
        fig = Visualizer.plot_waterfall({})
        assert isinstance(fig, go.Figure)

    def test_figure_has_waterfall_trace(self, sample_sankey_data):
        """Test that figure contains Waterfall trace."""
        fig = Visualizer.plot_waterfall(sample_sankey_data)
        assert len(fig.data) > 0
        assert isinstance(fig.data[0], go.Waterfall)


class TestPlotSentiment:
    """Tests for Visualizer.plot_sentiment method."""

    def test_returns_figure(self, sample_recommendations):
        """Test that plot_sentiment returns a Plotly Figure."""
        fig = Visualizer.plot_sentiment(sample_recommendations)
        assert isinstance(fig, go.Figure)

    def test_empty_dataframe_returns_none(self, empty_dataframe):
        """Test that empty DataFrame returns None."""
        result = Visualizer.plot_sentiment(empty_dataframe)
        assert result is None

    def test_figure_has_bar_trace(self, sample_recommendations):
        """Test that figure contains Bar trace."""
        fig = Visualizer.plot_sentiment(sample_recommendations)
        assert len(fig.data) > 0
        assert isinstance(fig.data[0], go.Bar)


class TestPlotHistoricalTrend:
    """Tests for Visualizer.plot_historical_trend method."""

    def test_returns_figure(self, sample_income_stmt):
        """Test that plot_historical_trend returns a Plotly Figure."""
        fig = Visualizer.plot_historical_trend(sample_income_stmt)
        assert isinstance(fig, go.Figure)

    def test_empty_dataframe_returns_empty_figure(self, empty_dataframe):
        """Test that empty DataFrame returns empty Figure."""
        fig = Visualizer.plot_historical_trend(empty_dataframe)
        assert isinstance(fig, go.Figure)

    def test_none_input_returns_empty_figure(self):
        """Test that None input returns empty Figure."""
        fig = Visualizer.plot_historical_trend(None)
        assert isinstance(fig, go.Figure)

    def test_custom_metrics(self, sample_income_stmt):
        """Test with custom metrics list."""
        custom_metrics = [("Total Revenue", "Revenue")]
        fig = Visualizer.plot_historical_trend(sample_income_stmt, metrics=custom_metrics)
        assert isinstance(fig, go.Figure)
        # Should have only one trace
        assert len(fig.data) == 1


class TestCalculateYoYMetrics:
    """Tests for Visualizer.calculate_yoy_metrics method."""

    def test_returns_dict(self, sample_income_stmt):
        """Test that calculate_yoy_metrics returns a dictionary."""
        result = Visualizer.calculate_yoy_metrics(sample_income_stmt)
        assert isinstance(result, dict)

    def test_contains_expected_metrics(self, sample_income_stmt):
        """Test that result contains expected metrics."""
        result = Visualizer.calculate_yoy_metrics(sample_income_stmt)
        assert 'Revenue' in result
        assert 'Net Income' in result

    def test_yoy_change_calculation(self, sample_income_stmt):
        """Test YoY change calculation."""
        result = Visualizer.calculate_yoy_metrics(sample_income_stmt)

        # Revenue: Q3=100B, Q2=95B -> YoY = (100-95)/95 * 100 = 5.26%
        current_val, yoy_change = result['Revenue']
        assert current_val == 100_000_000_000
        assert yoy_change is not None
        assert abs(yoy_change - 5.26) < 0.1  # Allow small floating point error

    def test_empty_dataframe(self, empty_dataframe):
        """Test with empty DataFrame."""
        result = Visualizer.calculate_yoy_metrics(empty_dataframe)
        assert result == {}

    def test_single_column_dataframe(self):
        """Test with single column DataFrame (can't calculate YoY)."""
        df = pd.DataFrame({'col1': {'Total Revenue': 100}})
        result = Visualizer.calculate_yoy_metrics(df)
        assert result == {}
