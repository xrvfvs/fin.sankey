# -*- coding: utf-8 -*-
"""
Internationalization (i18n) module for multi-language support.
"""

import streamlit as st


# Available languages
LANGUAGES = {
    'en': {
        'name': 'English',
        'flag': '🇺🇸',
    },
    'pl': {
        'name': 'Polski',
        'flag': '🇵🇱',
    }
}


# Translation dictionary
TRANSLATIONS = {
    # --- App Title & Subtitle ---
    'app_title': {
        'en': '🧩 fin.sankey | Financial Flow Visualizer',
        'pl': '🧩 fin.sankey | Wizualizacja Przepływów Finansowych',
    },
    'app_subtitle': {
        'en': 'Cash flow visualization for NASDAQ/S&P500 companies',
        'pl': 'Wizualizacja przepływów pieniężnych dla spółek NASDAQ/S&P500',
    },

    # --- Sidebar ---
    'configuration': {
        'en': 'Configuration',
        'pl': 'Konfiguracja',
    },
    'main_company': {
        'en': '1. Main Company',
        'pl': '1. Główna Spółka',
    },
    'search_company': {
        'en': 'Search for a company:',
        'pl': 'Wyszukaj spółkę:',
    },
    'your_watchlist': {
        'en': 'Your Watchlist:',
        'pl': 'Twoja Lista Obserwowanych:',
    },
    'quick_select': {
        'en': 'Quick select from watchlist:',
        'pl': 'Szybki wybór z listy:',
    },
    'add_to_watchlist': {
        'en': 'Add to Watchlist',
        'pl': 'Dodaj do Obserwowanych',
    },
    'remove_from_watchlist': {
        'en': 'Remove from Watchlist',
        'pl': 'Usuń z Obserwowanych',
    },
    'simulation': {
        'en': 'Simulation',
        'pl': 'Symulacja',
    },
    'revenue_change': {
        'en': 'Revenue Change (%)',
        'pl': 'Zmiana Przychodów (%)',
    },
    'cost_change': {
        'en': 'Cost Change (%)',
        'pl': 'Zmiana Kosztów (%)',
    },
    'reset_main': {
        'en': '↺ Reset (Main)',
        'pl': '↺ Reset (Główna)',
    },
    'benchmark': {
        'en': '2. Benchmark (Competitor)',
        'pl': '2. Benchmark (Konkurent)',
    },
    'compare_competitor': {
        'en': 'Compare with Competitor',
        'pl': 'Porównaj z Konkurentem',
    },
    'select_competitor': {
        'en': 'Select Competitor:',
        'pl': 'Wybierz Konkurenta:',
    },
    'reset_benchmark': {
        'en': '↺ Reset (Benchmark)',
        'pl': '↺ Reset (Benchmark)',
    },
    'reporting_period': {
        'en': '3. Reporting Period',
        'pl': '3. Okres Raportowania',
    },
    'select_period': {
        'en': 'Select period for analysis:',
        'pl': 'Wybierz okres do analizy:',
    },

    # --- Tabs ---
    'tab_viz': {
        'en': '📊 Viz & Benchmark',
        'pl': '📊 Wykresy & Benchmark',
    },
    'tab_metrics': {
        'en': '📈 Metrics Dashboard',
        'pl': '📈 Dashboard Wskaźników',
    },
    'tab_ai_report': {
        'en': '🤖 AI Report',
        'pl': '🤖 Raport AI',
    },
    'tab_extra': {
        'en': '📑 Extra Data',
        'pl': '📑 Dodatkowe Dane',
    },

    # --- Tab 1: Visualization ---
    'analysis': {
        'en': 'Analysis',
        'pl': 'Analiza',
    },
    'historical_trends': {
        'en': '📈 Historical Trends',
        'pl': '📈 Trendy Historyczne',
    },
    'yoy_changes': {
        'en': 'Year-over-Year Changes',
        'pl': 'Zmiany Rok do Roku',
    },
    'no_revenue_warning': {
        'en': '⚠️ Company reports no revenue or significant costs (likely SPAC or holding). Sankey chart cannot be generated.',
        'pl': '⚠️ Spółka nie raportuje przychodów ani znaczących kosztów (prawdopodobnie SPAC lub holding). Nie można wygenerować wykresu Sankey.',
    },

    # --- Tab 2: Metrics ---
    'metrics_dashboard': {
        'en': '📊 Metrics Dashboard',
        'pl': '📊 Dashboard Wskaźników',
    },
    'key_highlights': {
        'en': '🔹 Key Highlights',
        'pl': '🔹 Kluczowe Wskaźniki',
    },
    'valuation': {
        'en': '💲 Valuation',
        'pl': '💲 Wycena',
    },
    'financial_health': {
        'en': '🏦 Financial Health',
        'pl': '🏦 Kondycja Finansowa',
    },
    'profitability': {
        'en': '📈 Profitability',
        'pl': '📈 Rentowność',
    },

    # --- Tab 3: AI Report ---
    'ai_report_title': {
        'en': '🤖 AI Report (Perplexity Sonar)',
        'pl': '🤖 Raport AI (Perplexity Sonar)',
    },
    'ai_report_subtitle': {
        'en': 'This analysis combines fundamental data with the latest web news (Live Search).',
        'pl': 'Ta analiza łączy dane fundamentalne z najnowszymi wiadomościami z sieci (Live Search).',
    },
    'login_required': {
        'en': '🔒 Login required to generate AI reports. Create a free account to get started!',
        'pl': '🔒 Logowanie wymagane do generowania raportów AI. Utwórz darmowe konto, aby rozpocząć!',
    },
    'ai_reports_usage': {
        'en': '📊 AI Reports: {used}/{limit} used this month ({tier} tier)',
        'pl': '📊 Raporty AI: {used}/{limit} wykorzystanych w tym miesiącu (plan {tier})',
    },
    'ai_reports_unlimited': {
        'en': '📊 AI Reports: Unlimited ({tier} tier)',
        'pl': '📊 Raporty AI: Bez limitu (plan {tier})',
    },
    'global_cache_available': {
        'en': '🌐 Global cached report available ({age}) - saves API costs!',
        'pl': '🌐 Dostępny globalny cache raportu ({age}) - oszczędza koszty API!',
    },
    'load_cached': {
        'en': '📂 Load Cached Report',
        'pl': '📂 Wczytaj z Cache',
    },
    'generate_new': {
        'en': '🚀 Generate New Report',
        'pl': '🚀 Generuj Nowy Raport',
    },
    'generate_live': {
        'en': '🚀 Generate Live Report',
        'pl': '🚀 Generuj Raport Live',
    },
    'generating_report': {
        'en': '⏳ Perplexity is searching the web and analyzing data...',
        'pl': '⏳ Perplexity przeszukuje sieć i analizuje dane...',
    },
    'analysis_result': {
        'en': '### 📝 Analysis Result',
        'pl': '### 📝 Wynik Analizy',
    },
    'sources': {
        'en': '#### 📚 Sources / Citations',
        'pl': '#### 📚 Źródła / Cytowania',
    },
    'download_pdf': {
        'en': '📄 Download PDF Report',
        'pl': '📄 Pobierz Raport PDF',
    },
    'save_analysis': {
        'en': '💾 Save to My Analyses',
        'pl': '💾 Zapisz do Moich Analiz',
    },
    'upgrade_to_pro_pdf': {
        'en': '🔒 Upgrade to Pro to export PDFs',
        'pl': '🔒 Ulepsz do Pro, aby eksportować PDF',
    },

    # --- Tab 4: Extra Data ---
    'additional_data': {
        'en': 'Additional Data',
        'pl': 'Dodatkowe Dane',
    },
    'insider_trading': {
        'en': 'Insider Trading',
        'pl': 'Transakcje Insiderów',
    },
    'analyst_sentiment': {
        'en': 'Analyst Sentiment',
        'pl': 'Sentyment Analityków',
    },
    'no_insider_data': {
        'en': 'No insider trading data available.',
        'pl': 'Brak danych o transakcjach insiderów.',
    },
    'no_recommendations': {
        'en': 'No analyst recommendations available.',
        'pl': 'Brak rekomendacji analityków.',
    },
    'export_data': {
        'en': '📥 Export Financial Data',
        'pl': '📥 Eksportuj Dane Finansowe',
    },
    'export_description': {
        'en': 'Download raw financial data for further analysis in Excel.',
        'pl': 'Pobierz surowe dane finansowe do dalszej analizy w Excelu.',
    },
    'export_blocked_guest': {
        'en': '🔒 Excel export requires Pro tier. Login & upgrade to export data.',
        'pl': '🔒 Export do Excela wymaga planu Pro. Zaloguj się i ulepsz, aby eksportować.',
    },
    'export_blocked_free': {
        'en': '🔒 Excel export is available for Pro and Enterprise tiers. Upgrade to export data.',
        'pl': '🔒 Export do Excela dostępny dla planów Pro i Enterprise. Ulepsz, aby eksportować.',
    },
    'income_statement': {
        'en': '📊 Income Statement',
        'pl': '📊 Rachunek Zysków i Strat',
    },
    'balance_sheet': {
        'en': '📋 Balance Sheet',
        'pl': '📋 Bilans',
    },
    'all_data': {
        'en': '📦 All Data (Multi-sheet)',
        'pl': '📦 Wszystkie Dane (Wiele arkuszy)',
    },
    'my_saved_analyses': {
        'en': '📁 My Saved Analyses',
        'pl': '📁 Moje Zapisane Analizy',
    },
    'no_saved_analyses': {
        'en': "No saved analyses yet. Generate an AI report and click 'Save to My Analyses' to save it here.",
        'pl': "Brak zapisanych analiz. Wygeneruj raport AI i kliknij 'Zapisz do Moich Analiz', aby zapisać tutaj.",
    },
    'delete': {
        'en': 'Delete',
        'pl': 'Usuń',
    },

    # --- Auth ---
    'welcome': {
        'en': 'Welcome',
        'pl': 'Witaj',
    },
    'logout': {
        'en': 'Logout',
        'pl': 'Wyloguj',
    },
    'login': {
        'en': 'Login',
        'pl': 'Logowanie',
    },
    'register': {
        'en': 'Register',
        'pl': 'Rejestracja',
    },
    'email': {
        'en': 'Email',
        'pl': 'Email',
    },
    'password': {
        'en': 'Password',
        'pl': 'Hasło',
    },
    'confirm_password': {
        'en': 'Confirm Password',
        'pl': 'Potwierdź Hasło',
    },
    'create_account': {
        'en': 'Create Account',
        'pl': 'Utwórz Konto',
    },
    'login_success': {
        'en': 'Logged in successfully!',
        'pl': 'Zalogowano pomyślnie!',
    },
    'login_failed': {
        'en': 'Login failed',
        'pl': 'Logowanie nieudane',
    },
    'passwords_dont_match': {
        'en': "Passwords don't match",
        'pl': 'Hasła nie są zgodne',
    },
    'password_too_short': {
        'en': 'Password must be at least 6 characters',
        'pl': 'Hasło musi mieć co najmniej 6 znaków',
    },
    'account_created': {
        'en': 'Account created! Please check your email to confirm.',
        'pl': 'Konto utworzone! Sprawdź email, aby potwierdzić.',
    },
    'fill_all_fields': {
        'en': 'Please fill all fields',
        'pl': 'Proszę wypełnić wszystkie pola',
    },
    'enter_email_password': {
        'en': 'Please enter email and password',
        'pl': 'Proszę podać email i hasło',
    },

    # --- Tier limits ---
    'guest_periods_limit': {
        'en': '🔒 Guest: {limit} periods. Login for more.',
        'pl': '🔒 Gość: {limit} okresów. Zaloguj się, aby uzyskać więcej.',
    },
    'free_periods_limit': {
        'en': '🔒 Free tier: {limit} periods. Upgrade for more.',
        'pl': '🔒 Plan Free: {limit} okresów. Ulepsz, aby uzyskać więcej.',
    },
    'watchlist_full': {
        'en': 'Watchlist full',
        'pl': 'Lista obserwowanych pełna',
    },
    'limit_reached': {
        'en': 'Limit reached',
        'pl': 'Limit osiągnięty',
    },

    # --- Settings ---
    'settings': {
        'en': '⚙️ Settings',
        'pl': '⚙️ Ustawienia',
    },
    'language': {
        'en': 'Language',
        'pl': 'Język',
    },
    'theme': {
        'en': 'Theme',
        'pl': 'Motyw',
    },

    # --- Misc ---
    'select_company_prompt': {
        'en': 'Select a company from the list to start.',
        'pl': 'Wybierz spółkę z listy, aby rozpocząć.',
    },
    'no_data_available': {
        'en': 'No data available',
        'pl': 'Brak dostępnych danych',
    },
    'upgrade_to_pro': {
        'en': 'Upgrade to Pro',
        'pl': 'Ulepsz do Pro',
    },
    'no_historical_periods': {
        'en': 'No historical periods available',
        'pl': 'Brak dostępnych okresów historycznych',
    },
}


def init_language():
    """Initialize language in session state."""
    if 'language' not in st.session_state:
        st.session_state['language'] = 'en'  # Default language


def get_current_language():
    """Get current language code."""
    init_language()
    return st.session_state['language']


def set_language(lang_code):
    """Set current language."""
    if lang_code in LANGUAGES:
        st.session_state['language'] = lang_code


def t(key, **kwargs):
    """
    Translate a key to current language.

    Args:
        key: Translation key
        **kwargs: Format arguments for the translation string

    Returns:
        Translated string, or the key if not found
    """
    lang = get_current_language()

    if key in TRANSLATIONS:
        translation = TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get('en', key))
        if kwargs:
            try:
                return translation.format(**kwargs)
            except KeyError:
                return translation
        return translation

    return key


def render_language_selector():
    """Render language selector in sidebar."""
    init_language()
    current_lang = get_current_language()

    options = list(LANGUAGES.keys())
    labels = [f"{LANGUAGES[code]['flag']} {LANGUAGES[code]['name']}" for code in options]

    current_index = options.index(current_lang)

    selected_label = st.selectbox(
        t('language'),
        options=labels,
        index=current_index,
        key="language_selector"
    )

    selected_code = options[labels.index(selected_label)]

    if selected_code != current_lang:
        set_language(selected_code)
        st.rerun()


def get_available_languages():
    """Get list of available languages."""
    return LANGUAGES
