# -*- coding: utf-8 -*-
"""
Tests for modules/reports.py
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reports import ReportGenerator, PDFReport


class TestCleanText:
    """Tests for ReportGenerator.clean_text method."""

    def test_removes_zero_width_spaces(self):
        """Test that zero-width spaces are removed."""
        text = "Hello\u200bWorld"
        result = ReportGenerator.clean_text(text)
        assert "\u200b" not in result
        assert "HelloWorld" in result

    def test_replaces_non_breaking_space(self):
        """Test that non-breaking spaces are replaced with regular spaces."""
        text = "Hello\xa0World"
        result = ReportGenerator.clean_text(text)
        assert "\xa0" not in result
        assert "Hello World" in result

    def test_replaces_unicode_dashes(self):
        """Test that unicode dashes are replaced with regular dashes."""
        text = "value\u2013range"  # en-dash
        result = ReportGenerator.clean_text(text)
        assert "\u2013" not in result
        assert "value-range" in result

    def test_replaces_smart_quotes(self):
        """Test that smart quotes are replaced with regular quotes."""
        text = "\u201cHello\u201d"
        result = ReportGenerator.clean_text(text)
        assert "\u201c" not in result
        assert '"Hello"' in result

    def test_fixes_period_followed_by_capital(self):
        """Test that missing space after period is added."""
        text = "sentence.Next"
        result = ReportGenerator.clean_text(text)
        assert "sentence. Next" in result

    def test_fixes_dollar_number_letter(self):
        """Test that space is added between $number and letters."""
        text = "$28.75value"
        result = ReportGenerator.clean_text(text)
        assert "$28.75 value" in result

    def test_removes_double_spaces(self):
        """Test that double spaces are removed."""
        text = "Hello  World"
        result = ReportGenerator.clean_text(text)
        assert "  " not in result

    def test_handles_non_string_input(self):
        """Test that non-string input is converted to string."""
        result = ReportGenerator.clean_text(12345)
        assert result == "12345"

    def test_handles_none_like_input(self):
        """Test handling of None converted to string."""
        result = ReportGenerator.clean_text(None)
        assert result == "None"


class TestGenerateAiPrompt:
    """Tests for ReportGenerator.generate_ai_prompt method."""

    def test_returns_string(self, sample_sankey_data, sample_info):
        """Test that generate_ai_prompt returns a string."""
        prompt = ReportGenerator.generate_ai_prompt("AAPL", sample_sankey_data, sample_info)
        assert isinstance(prompt, str)

    def test_contains_ticker(self, sample_sankey_data, sample_info):
        """Test that prompt contains the ticker symbol."""
        prompt = ReportGenerator.generate_ai_prompt("AAPL", sample_sankey_data, sample_info)
        assert "AAPL" in prompt

    def test_contains_financial_data(self, sample_sankey_data, sample_info):
        """Test that prompt contains financial data."""
        prompt = ReportGenerator.generate_ai_prompt("AAPL", sample_sankey_data, sample_info)
        # Should contain revenue
        assert "100,000,000,000" in prompt or "100000000000" in prompt

    def test_contains_structure_sections(self, sample_sankey_data, sample_info):
        """Test that prompt contains required report sections."""
        prompt = ReportGenerator.generate_ai_prompt("AAPL", sample_sankey_data, sample_info)
        assert "INVESTMENT THESIS" in prompt
        assert "VALUATION" in prompt
        assert "KEY RISKS" in prompt


class TestCreatePdf:
    """Tests for ReportGenerator.create_pdf method."""

    def test_returns_bytes(self, sample_sankey_data, sample_info):
        """Test that create_pdf returns bytes."""
        metrics = {
            "Ticker": "AAPL",
            "P/E Ratio": "25.5",
            "Revenue": "$100B",
        }
        result = ReportGenerator.create_pdf(
            "AAPL",
            "Test analysis text with some content.",
            metrics,
            citations=[]
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_pdf_with_citations(self):
        """Test PDF generation with citations."""
        metrics = {"Ticker": "TEST"}
        citations = ["https://example.com/1", "https://example.com/2"]
        result = ReportGenerator.create_pdf(
            "TEST",
            "Analysis with citations.",
            metrics,
            citations=citations
        )
        assert isinstance(result, bytes)

    def test_pdf_with_markdown_formatting(self):
        """Test PDF generation with markdown text."""
        metrics = {"Ticker": "TEST"}
        text = """
# Heading
**Bold text** and *italic text*

- Bullet point 1
- Bullet point 2

| Column1 | Column2 |
|---------|---------|
| Data1   | Data2   |
"""
        result = ReportGenerator.create_pdf("TEST", text, metrics)
        assert isinstance(result, bytes)

    def test_pdf_with_unicode_characters(self):
        """Test PDF generation with unicode characters."""
        metrics = {"Ticker": "TEST"}
        text = "Price: €100, £50, ¥1000"
        result = ReportGenerator.create_pdf("TEST", text, metrics)
        assert isinstance(result, bytes)


class TestCacheOperations:
    """Tests for ReportGenerator cache operations."""

    def test_get_cache_path(self):
        """Test cache path generation."""
        path = ReportGenerator._get_cache_path("AAPL")
        assert "AAPL" in path
        assert path.endswith(".json")

    def test_save_and_get_cached_report(self):
        """Test saving and retrieving cached report."""
        # Use a temp directory for testing
        original_cache_dir = ReportGenerator.CACHE_DIR
        ReportGenerator.CACHE_DIR = tempfile.mkdtemp()

        try:
            report_data = {
                "text": "Test report content",
                "citations": ["https://example.com"]
            }

            # Save to cache
            result = ReportGenerator.save_report_to_cache("TEST_TICKER", report_data)
            assert result is True

            # Retrieve from cache
            cached, age = ReportGenerator.get_cached_report("TEST_TICKER")
            assert cached is not None
            assert cached["text"] == "Test report content"
            assert age < 1  # Should be less than 1 hour old

        finally:
            # Cleanup
            ReportGenerator.CACHE_DIR = original_cache_dir

    def test_expired_cache_returns_none(self):
        """Test that expired cache returns None."""
        original_cache_dir = ReportGenerator.CACHE_DIR
        original_ttl = ReportGenerator.CACHE_TTL_HOURS
        ReportGenerator.CACHE_DIR = tempfile.mkdtemp()
        ReportGenerator.CACHE_TTL_HOURS = 0  # Expire immediately

        try:
            report_data = {"text": "Test", "citations": []}
            ReportGenerator.save_report_to_cache("EXPIRED", report_data)

            cached, age = ReportGenerator.get_cached_report("EXPIRED")
            assert cached is None

        finally:
            ReportGenerator.CACHE_DIR = original_cache_dir
            ReportGenerator.CACHE_TTL_HOURS = original_ttl

    def test_nonexistent_cache_returns_none(self):
        """Test that nonexistent cache returns None."""
        cached, age = ReportGenerator.get_cached_report("NONEXISTENT_TICKER_12345")
        assert cached is None
        assert age is None


class TestPDFReport:
    """Tests for PDFReport class."""

    def test_default_font_family(self):
        """Test default font family is Helvetica."""
        assert PDFReport.font_family == 'Helvetica'

    def test_instantiation(self):
        """Test PDFReport can be instantiated."""
        pdf = PDFReport()
        assert pdf is not None

    def test_add_page(self):
        """Test adding a page to PDF."""
        pdf = PDFReport()
        pdf.add_page()
        assert pdf.page_no() == 1

    def test_chapter_title(self):
        """Test chapter_title method."""
        pdf = PDFReport()
        pdf.add_page()
        # Should not raise
        pdf.chapter_title("Test Chapter")

    def test_chapter_body(self):
        """Test chapter_body method."""
        pdf = PDFReport()
        pdf.add_page()
        # Should not raise
        pdf.chapter_body("This is the body text of the chapter.")
