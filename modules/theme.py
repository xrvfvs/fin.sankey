# -*- coding: utf-8 -*-
"""
Theme management module for Dark/Light mode.
"""

import streamlit as st


# Theme color definitions
THEMES = {
    'dark': {
        'name': 'Dark',
        'icon': '🌙',
        'backgroundColor': '#0E1117',
        'secondaryBackgroundColor': '#262730',
        'textColor': '#FAFAFA',
        'primaryColor': '#4285F4',
        'cardBackground': '#262730',
        'cardBorder': '#464b5c',
        'successColor': '#34A853',
        'errorColor': '#EA4335',
        'warningColor': '#FBBC05',
    },
    'light': {
        'name': 'Light',
        'icon': '☀️',
        'backgroundColor': '#FFFFFF',
        'secondaryBackgroundColor': '#F0F2F6',
        'textColor': '#31333F',
        'primaryColor': '#4285F4',
        'cardBackground': '#FFFFFF',
        'cardBorder': '#E0E0E0',
        'successColor': '#34A853',
        'errorColor': '#EA4335',
        'warningColor': '#FBBC05',
    }
}


def init_theme():
    """Initialize theme in session state."""
    if 'theme' not in st.session_state:
        st.session_state['theme'] = 'dark'  # Default theme


def get_current_theme():
    """Get current theme name."""
    init_theme()
    return st.session_state['theme']


def get_theme_config():
    """Get current theme configuration."""
    return THEMES[get_current_theme()]


def toggle_theme():
    """Toggle between dark and light theme."""
    init_theme()
    current = st.session_state['theme']
    st.session_state['theme'] = 'light' if current == 'dark' else 'dark'


def render_theme_toggle():
    """Render theme toggle button in sidebar."""
    init_theme()
    theme = get_theme_config()
    other_theme = THEMES['light' if get_current_theme() == 'dark' else 'dark']

    if st.button(f"{other_theme['icon']} {other_theme['name']} Mode", key="theme_toggle", use_container_width=True):
        toggle_theme()
        st.rerun()


def apply_theme_css():
    """Apply custom CSS based on current theme."""
    theme = get_theme_config()

    css = f"""
    <style>
    /* Main background */
    .stApp {{
        background-color: {theme['backgroundColor']};
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {theme['secondaryBackgroundColor']};
    }}

    /* Cards / Metrics */
    div[data-testid="stMetric"] {{
        background-color: {theme['cardBackground']};
        padding: 15px;
        border-radius: 8px;
        border: 1px solid {theme['cardBorder']};
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}

    /* Metric label */
    div[data-testid="stMetric"] label {{
        color: {theme['textColor']};
        opacity: 0.8;
    }}

    /* Metric value */
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {theme['textColor']};
    }}

    /* Expander */
    .streamlit-expanderHeader {{
        background-color: {theme['secondaryBackgroundColor']};
        border-radius: 8px;
    }}

    /* DataFrames */
    .stDataFrame {{
        background-color: {theme['cardBackground']};
        border-radius: 8px;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {theme['secondaryBackgroundColor']};
        border-radius: 8px;
        padding: 4px;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 6px;
        padding: 8px 16px;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: {theme['primaryColor']};
    }}

    /* Buttons - consistent styling */
    .stButton > button {{
        border-radius: 8px;
        transition: all 0.2s ease;
        font-weight: 500;
        padding: 0.5rem 1rem;
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }}

    /* Primary buttons (type="primary") */
    .stButton > button[kind="primary"] {{
        background-color: {theme['primaryColor']};
        color: white;
        border: none;
    }}

    /* Secondary buttons - subtle styling */
    .stButton > button[kind="secondary"] {{
        background-color: transparent;
        border: 1px solid {theme['cardBorder']};
        color: {theme['textColor']};
    }}

    .stButton > button[kind="secondary"]:hover {{
        background-color: {theme['secondaryBackgroundColor']};
    }}

    /* Info/Warning/Error boxes */
    .stAlert {{
        border-radius: 8px;
    }}

    /* Form inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {{
        background-color: {theme['cardBackground']};
        border-color: {theme['cardBorder']};
        border-radius: 8px;
    }}

    /* Dividers */
    hr {{
        border-color: {theme['cardBorder']};
    }}

    /* Download buttons */
    .stDownloadButton > button {{
        background-color: {theme['successColor']};
        color: white;
        border: none;
    }}

    .stDownloadButton > button:hover {{
        background-color: {theme['successColor']};
        opacity: 0.9;
    }}

    /* Caption text */
    .stCaption {{
        color: {theme['textColor']};
        opacity: 0.7;
    }}

    /* Markdown headers - visual hierarchy */
    h1 {{
        color: {theme['textColor']};
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }}

    h2 {{
        color: {theme['textColor']};
        font-size: 1.5rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid {theme['cardBorder']};
    }}

    h3 {{
        color: {theme['textColor']};
        font-size: 1.25rem;
        font-weight: 600;
        margin-top: 1rem;
    }}

    h4 {{
        color: {theme['textColor']};
        font-size: 1rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.9;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }}

    h5, h6 {{
        color: {theme['textColor']};
        font-weight: 500;
    }}

    /* Code blocks */
    code {{
        background-color: {theme['secondaryBackgroundColor']};
        border-radius: 4px;
        padding: 2px 6px;
    }}

    /* Scrollbar (webkit) */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: {theme['secondaryBackgroundColor']};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {theme['cardBorder']};
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {theme['primaryColor']};
    }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


def get_plotly_template():
    """Get Plotly template based on current theme."""
    if get_current_theme() == 'dark':
        return 'plotly_dark'
    return 'plotly_white'


def get_chart_colors():
    """Get chart color palette based on current theme."""
    theme = get_theme_config()
    return {
        'primary': theme['primaryColor'],
        'success': theme['successColor'],
        'error': theme['errorColor'],
        'warning': theme['warningColor'],
        'background': theme['backgroundColor'],
        'text': theme['textColor'],
    }
