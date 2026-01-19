# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures for Financial Sankey tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


@pytest.fixture
def sample_income_stmt():
    """Create a sample income statement DataFrame for testing."""
    dates = pd.to_datetime(['2024-09-30', '2024-06-30', '2024-03-31', '2023-12-31'])
    data = {
        dates[0]: {
            'Total Revenue': 100_000_000_000,
            'Cost Of Revenue': 40_000_000_000,
            'Gross Profit': 60_000_000_000,
            'Operating Expense': 20_000_000_000,
            'Research And Development': 8_000_000_000,
            'Selling General And Administration': 10_000_000_000,
            'Operating Income': 40_000_000_000,
            'Tax Provision': 8_000_000_000,
            'Interest Expense': 1_000_000_000,
            'Net Income': 31_000_000_000,
            'Pretax Income': 39_000_000_000,
        },
        dates[1]: {
            'Total Revenue': 95_000_000_000,
            'Cost Of Revenue': 38_000_000_000,
            'Gross Profit': 57_000_000_000,
            'Operating Expense': 19_000_000_000,
            'Research And Development': 7_500_000_000,
            'Selling General And Administration': 9_500_000_000,
            'Operating Income': 38_000_000_000,
            'Tax Provision': 7_600_000_000,
            'Interest Expense': 900_000_000,
            'Net Income': 29_500_000_000,
            'Pretax Income': 37_100_000_000,
        },
        dates[2]: {
            'Total Revenue': 90_000_000_000,
            'Cost Of Revenue': 36_000_000_000,
            'Gross Profit': 54_000_000_000,
            'Operating Expense': 18_000_000_000,
            'Research And Development': 7_000_000_000,
            'Selling General And Administration': 9_000_000_000,
            'Operating Income': 36_000_000_000,
            'Tax Provision': 7_200_000_000,
            'Interest Expense': 850_000_000,
            'Net Income': 27_950_000_000,
            'Pretax Income': 35_150_000_000,
        },
        dates[3]: {
            'Total Revenue': 85_000_000_000,
            'Cost Of Revenue': 34_000_000_000,
            'Gross Profit': 51_000_000_000,
            'Operating Expense': 17_000_000_000,
            'Research And Development': 6_500_000_000,
            'Selling General And Administration': 8_500_000_000,
            'Operating Income': 34_000_000_000,
            'Tax Provision': 6_800_000_000,
            'Interest Expense': 800_000_000,
            'Net Income': 26_400_000_000,
            'Pretax Income': 33_200_000_000,
        },
    }
    df = pd.DataFrame(data)
    return df


@pytest.fixture
def sample_balance_sheet():
    """Create a sample balance sheet DataFrame for testing."""
    dates = pd.to_datetime(['2024-09-30', '2024-06-30'])
    data = {
        dates[0]: {
            'Total Assets': 500_000_000_000,
            'Total Stockholder Equity': 150_000_000_000,
            'Total Debt': 100_000_000_000,
            'Cash And Cash Equivalents': 50_000_000_000,
        },
        dates[1]: {
            'Total Assets': 480_000_000_000,
            'Total Stockholder Equity': 145_000_000_000,
            'Total Debt': 95_000_000_000,
            'Cash And Cash Equivalents': 48_000_000_000,
        },
    }
    df = pd.DataFrame(data)
    return df


@pytest.fixture
def sample_info():
    """Create a sample company info dictionary for testing."""
    return {
        'symbol': 'TEST',
        'shortName': 'Test Company Inc.',
        'currency': 'USD',
        'currentPrice': 150.50,
        'regularMarketPrice': 150.50,
        'previousClose': 149.00,
        'trailingPE': 25.5,
        'forwardPE': 22.0,
        'priceToBook': 8.5,
        'priceToSalesTrailing12Months': 6.2,
        'pegRatio': 1.8,
        'debtToEquity': 65.5,
        'returnOnEquity': 0.45,
        'grossMargins': 0.60,
        'operatingMargins': 0.40,
        'profitMargins': 0.31,
        'beta': 1.2,
        'marketCap': 2_500_000_000_000,
        'enterpriseToRevenue': 5.8,
        'enterpriseToEbitda': 18.5,
        'totalRevenue': 100_000_000_000,
        'totalDebt': 100_000_000_000,
        'sharesOutstanding': 16_000_000_000,
        'bookValue': 17.75,
        'currentRatio': 1.5,
        'quickRatio': 1.2,
        'revenuePerShare': 6.25,
        'trailingEps': 5.90,
        'fullTimeEmployees': 150000,
    }


@pytest.fixture
def sample_sankey_data():
    """Create sample Sankey data for testing."""
    return {
        'Revenue': 100_000_000_000,
        'COGS': 40_000_000_000,
        'Gross Profit': 60_000_000_000,
        'OpEx_Total': 20_000_000_000,
        'R&D': 8_000_000_000,
        'SG&A': 10_000_000_000,
        'Other OpEx': 2_000_000_000,
        'Operating Profit': 40_000_000_000,
        'Taxes': 8_000_000_000,
        'Interest': 1_000_000_000,
        'Net Income': 31_000_000_000,
    }


@pytest.fixture
def sample_recommendations():
    """Create sample analyst recommendations DataFrame."""
    data = {
        'strongBuy': [10, 12, 8, 15],
        'buy': [20, 18, 22, 19],
        'hold': [15, 14, 16, 12],
        'sell': [3, 4, 2, 5],
        'strongSell': [1, 1, 0, 2],
    }
    index = pd.to_datetime(['2024-01', '2024-02', '2024-03', '2024-04'])
    return pd.DataFrame(data, index=index)


@pytest.fixture
def empty_dataframe():
    """Create an empty DataFrame for testing edge cases."""
    return pd.DataFrame()
