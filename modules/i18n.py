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
        'en': 'fin.sankey',
        'pl': 'fin.sankey',
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
        'en': 'Visualization',
        'pl': 'Wykresy',
    },
    'tab_metrics': {
        'en': 'Metrics',
        'pl': 'Wskaźniki',
    },
    'tab_ai_report': {
        'en': 'AI Report',
        'pl': 'Raport AI',
    },
    'tab_extra': {
        'en': 'Data & News',
        'pl': 'Dane i News',
    },
    'tab_portfolio': {
        'en': 'Portfolio',
        'pl': 'Portfel',
    },

    # --- Tab 1: Visualization ---
    'analysis': {
        'en': 'Analysis',
        'pl': 'Analiza',
    },
    'historical_trends': {
        'en': 'Historical Trends',
        'pl': 'Trendy Historyczne',
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
        'en': 'Metrics Dashboard',
        'pl': 'Dashboard Wskaźników',
    },
    'key_highlights': {
        'en': 'Key Highlights',
        'pl': 'Kluczowe Wskaźniki',
    },
    'valuation': {
        'en': 'Valuation',
        'pl': 'Wycena',
    },
    'financial_health': {
        'en': 'Financial Health',
        'pl': 'Kondycja Finansowa',
    },
    'profitability': {
        'en': 'Profitability',
        'pl': 'Rentowność',
    },

    # --- Tab 3: AI Report ---
    'ai_report_title': {
        'en': 'AI Report',
        'pl': 'Raport AI',
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
        'en': 'Searching the web and analyzing financial data... This may take 15-30 seconds.',
        'pl': 'Przeszukiwanie sieci i analiza danych finansowych... To może potrwać 15-30 sekund.',
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
        'en': 'Export Financial Data',
        'pl': 'Eksportuj Dane Finansowe',
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
        'en': 'My Saved Analyses',
        'pl': 'Moje Zapisane Analizy',
    },
    'no_saved_analyses': {
        'en': "No saved analyses yet. Go to the AI Report tab to generate and save your first analysis.",
        'pl': "Brak zapisanych analiz. Przejdź do zakładki Raport AI, aby wygenerować i zapisać pierwszą analizę.",
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
    'supabase_not_configured': {
        'en': 'Authentication is not configured. Set Supabase credentials in .streamlit/secrets.toml to enable login.',
        'pl': 'Uwierzytelnianie nie jest skonfigurowane. Ustaw dane Supabase w .streamlit/secrets.toml, aby włączyć logowanie.',
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

    # --- News Feed ---
    'news_title': {
        'en': 'Latest News for {ticker}',
        'pl': 'Najnowsze wiadomości dla {ticker}',
    },
    'latest_news': {
        'en': 'Latest News',
        'pl': 'Najnowsze Wiadomości',
    },
    'no_news_available': {
        'en': 'No news available for {ticker}',
        'pl': 'Brak wiadomości dla {ticker}',
    },
    'news_sentiment': {
        'en': 'News Sentiment',
        'pl': 'Sentyment Wiadomości',
    },
    'positive_news': {
        'en': 'Positive',
        'pl': 'Pozytywne',
    },
    'negative_news': {
        'en': 'Negative',
        'pl': 'Negatywne',
    },
    'neutral_news': {
        'en': 'Neutral',
        'pl': 'Neutralne',
    },

    # --- Portfolio & Technical Analysis ---
    'portfolio': {
        'en': 'Portfolio',
        'pl': 'Portfel',
    },
    'portfolio_tracker': {
        'en': 'Portfolio Tracker',
        'pl': 'Śledzenie Portfela',
    },
    'portfolio_empty': {
        'en': 'No positions yet. Use the form above to add your first holding.',
        'pl': 'Brak pozycji. Użyj formularza powyżej, aby dodać pierwszą pozycję.',
    },
    'total_value': {
        'en': 'Total Value',
        'pl': 'Wartość Całkowita',
    },
    'total_gain': {
        'en': 'Total Gain/Loss',
        'pl': 'Zysk/Strata',
    },
    'daily_change': {
        'en': 'Daily Change',
        'pl': 'Zmiana Dzienna',
    },
    'positions': {
        'en': 'Positions',
        'pl': 'Pozycje',
    },
    'holdings': {
        'en': 'Holdings',
        'pl': 'Aktywa',
    },
    'add_position': {
        'en': 'Add Position',
        'pl': 'Dodaj Pozycję',
    },
    'shares': {
        'en': 'Shares',
        'pl': 'Akcje',
    },
    'avg_cost': {
        'en': 'Average Cost',
        'pl': 'Średni Koszt',
    },
    'ticker': {
        'en': 'Ticker',
        'pl': 'Ticker',
    },
    'technical_analysis': {
        'en': 'Technical Analysis',
        'pl': 'Analiza Techniczna',
    },
    'loading_indicators': {
        'en': 'Calculating technical indicators...',
        'pl': 'Obliczanie wskaźników technicznych...',
    },
    'insufficient_data_for_analysis': {
        'en': 'Insufficient data for technical analysis',
        'pl': 'Niewystarczające dane do analizy technicznej',
    },
    'current_price': {
        'en': 'Current Price',
        'pl': 'Aktualna Cena',
    },
    'overall_signal': {
        'en': 'Overall Signal',
        'pl': 'Sygnał Ogólny',
    },
    'portfolio_limit_reached': {
        'en': 'Portfolio limit reached ({used}/{limit}). Upgrade to Pro for more positions!',
        'pl': 'Limit portfela osiągnięty ({used}/{limit}). Ulepsz do Pro, aby dodać więcej pozycji!',
    },

    # --- Price Alerts ---
    'price_alerts': {
        'en': 'Price Alerts',
        'pl': 'Alerty Cenowe',
    },
    'create_alert': {
        'en': 'Create Alert',
        'pl': 'Utwórz Alert',
    },
    'alert_type': {
        'en': 'Alert Type',
        'pl': 'Typ Alertu',
    },
    'target_price': {
        'en': 'Target Price ($)',
        'pl': 'Cena Docelowa ($)',
    },
    'target_percent': {
        'en': 'Target Change (%)',
        'pl': 'Docelowa Zmiana (%)',
    },
    'change_from_current': {
        'en': 'change from current price',
        'pl': 'zmiana od aktualnej ceny',
    },
    'your_alerts': {
        'en': 'Your Alerts',
        'pl': 'Twoje Alerty',
    },
    'no_alerts': {
        'en': 'No price alerts configured. Create an alert above to get notified when a stock reaches your target price.',
        'pl': 'Brak skonfigurowanych alertów. Utwórz alert powyżej, aby otrzymać powiadomienie gdy akcja osiągnie docelową cenę.',
    },
    'alerts_triggered': {
        'en': 'alerts triggered',
        'pl': 'alertów wyzwolonych',
    },
    'enter_ticker': {
        'en': 'Please enter a ticker symbol',
        'pl': 'Wprowadź symbol tickera',
    },
    'alerts_limit_reached': {
        'en': 'Alerts limit reached ({used}/{limit}). Upgrade to Pro for more alerts!',
        'pl': 'Limit alertów osiągnięty ({used}/{limit}). Ulepsz do Pro, aby dodać więcej alertów!',
    },

    # --- Email Notifications ---
    'email_notifications': {
        'en': 'Email Notifications',
        'pl': 'Powiadomienia Email',
    },
    'email_not_configured': {
        'en': 'Email notifications are not configured. Contact administrator.',
        'pl': 'Powiadomienia email nie są skonfigurowane. Skontaktuj się z administratorem.',
    },
    'email_configured': {
        'en': 'Email configured',
        'pl': 'Email skonfigurowany',
    },
    'receive_alert_emails': {
        'en': 'Receive alert emails',
        'pl': 'Otrzymuj alerty emailem',
    },
    'receive_daily_summary': {
        'en': 'Receive daily summary',
        'pl': 'Otrzymuj dzienne podsumowanie',
    },
    'send_test_email': {
        'en': 'Send Test Email',
        'pl': 'Wyślij Email Testowy',
    },
    'test_email_sent': {
        'en': 'Test email sent to {email}',
        'pl': 'Email testowy wysłany na {email}',
    },
    'test_email_failed': {
        'en': 'Failed to send test email',
        'pl': 'Nie udało się wysłać emaila testowego',
    },
    'login_for_test_email': {
        'en': 'Please log in to send test email',
        'pl': 'Zaloguj się, aby wysłać email testowy',
    },

    # --- Executive Summary Dashboard ---
    'executive_summary': {
        'en': 'Executive Summary',
        'pl': 'Podsumowanie Wykonawcze',
    },
    'company_overview': {
        'en': 'Company Overview',
        'pl': 'Przegląd Spółki',
    },
    'quick_stats': {
        'en': 'Quick Stats',
        'pl': 'Szybkie Statystyki',
    },
    'market_position': {
        'en': 'Market Position',
        'pl': 'Pozycja Rynkowa',
    },
    'health_score': {
        'en': 'Health Score',
        'pl': 'Ocena Kondycji',
    },
    'sector': {
        'en': 'Sector',
        'pl': 'Sektor',
    },
    'industry': {
        'en': 'Industry',
        'pl': 'Branża',
    },
    'employees': {
        'en': 'Employees',
        'pl': 'Pracownicy',
    },
    'founded': {
        'en': 'Founded',
        'pl': 'Założona',
    },
    'headquarters': {
        'en': 'Headquarters',
        'pl': 'Siedziba',
    },
    'website': {
        'en': 'Website',
        'pl': 'Strona WWW',
    },

    # --- Cache Status Indicator ---
    'cache_status': {
        'en': 'Cache Status',
        'pl': 'Status Cache',
    },
    'cache_fresh': {
        'en': 'Fresh data',
        'pl': 'Świeże dane',
    },
    'cache_from_cache': {
        'en': 'From cache',
        'pl': 'Z cache',
    },
    'cache_age': {
        'en': '{hours}h {minutes}m ago',
        'pl': '{hours}h {minutes}m temu',
    },
    'data_cached': {
        'en': 'Data cached for faster loading',
        'pl': 'Dane w cache dla szybszego ładowania',
    },
    'last_updated': {
        'en': 'Last updated',
        'pl': 'Ostatnia aktualizacja',
    },

    # --- Data Table ---
    'search_table': {
        'en': 'Search in table...',
        'pl': 'Szukaj w tabeli...',
    },
    'rows_per_page': {
        'en': 'Rows per page',
        'pl': 'Wierszy na stronę',
    },
    'showing_rows': {
        'en': 'Showing {start}-{end} of {total}',
        'pl': 'Wyświetlanie {start}-{end} z {total}',
    },
}


# Metric tooltips with explanations
METRIC_TOOLTIPS = {
    'revenue_per_share': {
        'en': 'Revenue Per Share = Total Revenue / Shares Outstanding. Shows how much revenue the company generates per share. Higher is generally better.',
        'pl': 'Przychód na Akcję = Całkowite Przychody / Liczba Akcji. Pokazuje ile przychodów firma generuje na jedną akcję. Wyższa wartość jest lepsza.',
    },
    'eps': {
        'en': 'Earnings Per Share (EPS) = Net Income / Shares Outstanding. Shows profit allocated to each share. Key metric for valuation.',
        'pl': 'Zysk na Akcję (EPS) = Zysk Netto / Liczba Akcji. Pokazuje zysk przypadający na każdą akcję. Kluczowy wskaźnik wyceny.',
    },
    'roe': {
        'en': "Return on Equity (ROE) = Net Income / Shareholders' Equity. Measures profitability relative to shareholders' investment. >15% is typically good.",
        'pl': 'Zwrot z Kapitału Własnego (ROE) = Zysk Netto / Kapitał Własny. Mierzy rentowność w stosunku do inwestycji akcjonariuszy. >15% jest zwykle dobry.',
    },
    'roic': {
        'en': 'Return on Invested Capital (ROIC) = NOPAT / (Equity + Debt - Cash). Measures how efficiently capital is used. >10% indicates good capital allocation.',
        'pl': 'Zwrot z Zainwestowanego Kapitału (ROIC) = NOPAT / (Kapitał + Dług - Gotówka). Mierzy efektywność wykorzystania kapitału. >10% wskazuje dobrą alokację.',
    },
    'debt_to_equity': {
        'en': 'Debt to Equity = Total Debt / Total Equity. Shows financial leverage. <1 is conservative, >2 may indicate high risk.',
        'pl': 'Dług do Kapitału = Całkowity Dług / Kapitał Własny. Pokazuje dźwignię finansową. <1 jest konserwatywny, >2 może wskazywać wysokie ryzyko.',
    },
    'book_value': {
        'en': 'Book Value Per Share = (Assets - Liabilities) / Shares. Represents the net asset value per share. Important for value investors.',
        'pl': 'Wartość Księgowa na Akcję = (Aktywa - Zobowiązania) / Akcje. Reprezentuje wartość netto aktywów na akcję. Ważne dla inwestorów wartościowych.',
    },
    'current_ratio': {
        'en': 'Current Ratio = Current Assets / Current Liabilities. Measures short-term liquidity. >1.5 is healthy, <1 may signal trouble.',
        'pl': 'Wskaźnik Płynności Bieżącej = Aktywa Bieżące / Zobowiązania Bieżące. Mierzy płynność krótkoterminową. >1.5 jest zdrowy, <1 może sygnalizować problemy.',
    },
    'quick_ratio': {
        'en': 'Quick Ratio = (Current Assets - Inventory) / Current Liabilities. Stricter liquidity test excluding inventory. >1 is generally safe.',
        'pl': 'Wskaźnik Szybki = (Aktywa Bieżące - Zapasy) / Zobowiązania Bieżące. Bardziej rygorystyczny test płynności. >1 jest bezpieczny.',
    },
    'pe_ratio': {
        'en': 'Price to Earnings (P/E) = Stock Price / EPS. Shows how much investors pay per dollar of earnings. Compare with industry average.',
        'pl': 'Cena do Zysku (P/E) = Cena Akcji / EPS. Pokazuje ile inwestorzy płacą za dolara zysku. Porównaj ze średnią branżową.',
    },
    'ps_ratio': {
        'en': 'Price to Sales (P/S) = Market Cap / Revenue. Useful for companies with no earnings. Lower values may indicate undervaluation.',
        'pl': 'Cena do Sprzedaży (P/S) = Kapitalizacja / Przychody. Przydatny dla firm bez zysków. Niższe wartości mogą wskazywać niedowartościowanie.',
    },
    'pb_ratio': {
        'en': 'Price to Book (P/B) = Stock Price / Book Value. <1 may indicate undervaluation, but check asset quality.',
        'pl': 'Cena do Wartości Księgowej (P/B) = Cena Akcji / Wartość Księgowa. <1 może wskazywać niedowartościowanie.',
    },
    'peg_ratio': {
        'en': 'PEG Ratio = P/E / Earnings Growth Rate. Accounts for growth. <1 suggests undervaluation relative to growth.',
        'pl': 'Wskaźnik PEG = P/E / Stopa Wzrostu Zysków. Uwzględnia wzrost. <1 sugeruje niedowartościowanie względem wzrostu.',
    },
    'ev_revenue': {
        'en': 'EV/Revenue = Enterprise Value / Revenue. Compares total company value to sales. Useful for comparing companies with different capital structures.',
        'pl': 'EV/Przychody = Wartość Przedsiębiorstwa / Przychody. Porównuje całkowitą wartość firmy ze sprzedażą.',
    },
    'ev_ebitda': {
        'en': 'EV/EBITDA = Enterprise Value / EBITDA. Popular valuation metric. Lower values may indicate better value. Industry-specific benchmarks apply.',
        'pl': 'EV/EBITDA = Wartość Przedsiębiorstwa / EBITDA. Popularny wskaźnik wyceny. Niższe wartości mogą wskazywać lepszą wartość.',
    },
    'market_cap': {
        'en': 'Market Capitalization = Stock Price x Shares Outstanding. Total market value of the company.',
        'pl': 'Kapitalizacja Rynkowa = Cena Akcji x Liczba Akcji. Całkowita wartość rynkowa firmy.',
    },
    'forward_pe': {
        'en': 'Forward P/E = Stock Price / Expected EPS. Based on analyst estimates for future earnings.',
        'pl': 'Forward P/E = Cena Akcji / Oczekiwany EPS. Oparty na prognozach analityków dotyczących przyszłych zysków.',
    },
    'gross_margin': {
        'en': 'Gross Margin = (Revenue - COGS) / Revenue. Shows production efficiency. Higher margins indicate pricing power.',
        'pl': 'Marża Brutto = (Przychody - Koszty Sprzedaży) / Przychody. Pokazuje efektywność produkcji. Wyższe marże wskazują siłę cenową.',
    },
    'operating_margin': {
        'en': 'Operating Margin = Operating Income / Revenue. Shows operational efficiency after all operating expenses.',
        'pl': 'Marża Operacyjna = Dochód Operacyjny / Przychody. Pokazuje efektywność operacyjną po wszystkich kosztach operacyjnych.',
    },
    'profit_margin': {
        'en': 'Profit Margin = Net Income / Revenue. Shows overall profitability after all expenses and taxes.',
        'pl': 'Marża Zysku = Zysk Netto / Przychody. Pokazuje ogólną rentowność po wszystkich kosztach i podatkach.',
    },
    'beta': {
        'en': "Beta measures stock volatility vs market. Beta=1 means same volatility as market. >1 is more volatile, <1 is less volatile.",
        'pl': 'Beta mierzy zmienność akcji względem rynku. Beta=1 oznacza taką samą zmienność jak rynek. >1 jest bardziej zmienny, <1 jest mniej zmienny.',
    },
    'debt_to_assets': {
        'en': 'Debt to Assets = Total Debt / Total Assets. Shows what portion of assets is financed by debt.',
        'pl': 'Dług do Aktywów = Całkowity Dług / Całkowite Aktywa. Pokazuje jaką część aktywów finansuje dług.',
    },
    'assets_per_share': {
        'en': 'Assets Per Share = Total Assets / Shares Outstanding. Shows asset backing per share.',
        'pl': 'Aktywa na Akcję = Całkowite Aktywa / Liczba Akcji. Pokazuje pokrycie aktywami na akcję.',
    },
    'revenue_per_employee': {
        'en': 'Revenue Per Employee = Total Revenue / Number of Employees. Measures workforce productivity.',
        'pl': 'Przychód na Pracownika = Całkowite Przychody / Liczba Pracowników. Mierzy produktywność siły roboczej.',
    },
}


def get_tooltip(metric_key: str) -> str:
    """Get tooltip text for a metric in current language."""
    lang = get_current_language()
    if metric_key in METRIC_TOOLTIPS:
        return METRIC_TOOLTIPS[metric_key].get(lang, METRIC_TOOLTIPS[metric_key].get('en', ''))
    return ''


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
