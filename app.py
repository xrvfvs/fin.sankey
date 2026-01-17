
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 23 13:56:21 2025

@author: rafal
"""
import openai
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from fpdf import FPDF
import datetime
import os
import urllib.request



# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="san.key - Advanced Financial Viz",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. DATA FETCHING MODULE ---
class DataManager:
    """Class responsible for fetching and processing data from yfinance."""
    
    @staticmethod
    @st.cache_data(ttl=86400) 
    def get_tickers_list():
        """
        Retrieves a list of tickers and filters out potential SPACs based on name.
        """
        all_tickers = set()
        
        # Keywords typical for companies without revenue (SPAC / Shell / ETFs)
        spac_keywords = ["ACQUISITION", "MERGER", "BLANK CHECK", "CAPITAL CORP", "HOLDINGS CORP", "SPAC", "ETF", "2X", "1X"]
        
        # Helper function
        def is_clean(name):
            name_upper = str(name).upper()
            for kw in spac_keywords:
                if kw in name_upper:
                    return False
            return True

        # 1. Attempt NASDAQ (Full list)
        try:
            url = "http://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
            df = pd.read_csv(url, sep="|")
            # Remove the last row (often metadata/footer)
            if not df.empty:
                df = df[:-1]
                
            for _, row in df.iterrows():
                symbol = str(row['Symbol'])
                name = str(row['Security Name'])
                if is_clean(name):
                    all_tickers.add(f"{symbol} | {name}")
        except Exception: 
            pass

        # 2. Backup S&P 500 (Always safe)
        try:
            df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
            for _, row in df.iterrows():
                symbol = row['Symbol'].replace('.', '-')
                name = row['Security']
                all_tickers.add(f"{symbol} | {name}")
        except Exception: 
            pass
            
        # 3. Backup NASDAQ-100
        try:
            dfs = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')
            for df in dfs:
                # Search for the ticker table
                if 'Ticker' in df.columns or 'Symbol' in df.columns:
                    col_name = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
                    name_col = 'Company' if 'Company' in df.columns else 'Security'
                    
                    if name_col in df.columns:
                        for _, row in df.iterrows():
                            all_tickers.add(f"{row[col_name]} | {row[name_col]}")
                        break
        except Exception: 
            pass

        # Fallback in case of no internet/errors
        if not all_tickers:
            return ["AAPL | Apple Inc.", "MSFT | Microsoft Corp", "NVDA | Nvidia Corp", "GOOGL | Alphabet Inc."]

        return sorted(list(all_tickers))

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_financials(ticker_symbol):
        try:
            ticker = yf.Ticker(ticker_symbol)
            
            # Force fetching to check if data exists
            income_stmt = ticker.income_stmt
            balance_sheet = ticker.balance_sheet
            info = ticker.info
            
            # Fetch extras (might fail)
            insider = getattr(ticker, 'insider_purchases', pd.DataFrame())
            recommendations = getattr(ticker, 'recommendations', pd.DataFrame())

            if income_stmt is None or income_stmt.empty:
                return None
                
            return {
                "income_stmt": income_stmt,
                "balance_sheet": balance_sheet,
                "info": info,
                "insider": insider,
                "recommendations": recommendations
            }
        except Exception as e:
            st.error(f"Error fetching data for {ticker_symbol}: {e}")
            return None

    @staticmethod
    def extract_sankey_data(income_stmt, revenue_mod=1.0, cost_mod=1.0):
        """Extract detailed data in 'Google-like' style."""
        try:
            if income_stmt is None or income_stmt.empty:
                return {}

            latest = income_stmt.iloc[:, 0]
            
            def get_val(keys):
                for k in keys:
                    if k in latest.index:
                        val = latest[k]
                        return float(val) if pd.notnull(val) else 0.0
                return 0.0

            # 1. Revenue & COGS
            revenue = get_val(["Total Revenue", "Revenue"]) * revenue_mod
            cogs = get_val(["Cost Of Revenue", "Cost of Goods Sold"]) * cost_mod
            gross_profit = revenue - cogs
            
            # 2. Operating Expenses (Detailed)
            opex_total = get_val(["Operating Expense", "Total Operating Expenses"])
            rnd = get_val(["Research And Development"])
            sga = get_val(["Selling General And Administration"])
            
            # The rest of OpEx is "Other OpEx"
            other_opex = opex_total - rnd - sga
            if other_opex < 0: other_opex = 0 # Data safety check
            
            # 3. Operating Profit (Calculated)
            op_profit = gross_profit - opex_total
            
            # 4. Taxes and Interest
            taxes = get_val(["Tax Provision", "Income Tax Expense"])
            interest = abs(get_val(["Interest Expense", "Interest Income Expense Net"]))
            
            # 5. Net Income (Calculated for consistency)
            net_income = op_profit - taxes - interest
            
            return {
                "Revenue": revenue,
                "COGS": cogs,
                "Gross Profit": gross_profit,
                "OpEx_Total": opex_total,
                "R&D": rnd,
                "SG&A": sga,
                "Other OpEx": other_opex,
                "Operating Profit": op_profit,
                "Taxes": taxes,
                "Interest": interest,
                "Net Income": net_income
            }
        except Exception as e:
            st.error(f"Error processing data: {e}")
            return {}

# --- 2. VISUALIZATION MODULE ---
class Visualizer:
    """Visualization class in App Economy Insights style."""
    
    @staticmethod
    def _fmt(val):
        """Helper number formatter (e.g., 50B)."""
        if val >= 1e12: return f"${val/1e12:.1f}T"
        if val >= 1e9: return f"${val/1e9:.1f}B"
        if val >= 1e6: return f"${val/1e6:.1f}M"
        return f"${val:.0f}"

    @staticmethod
    def plot_sankey(data, title_suffix=""):
        if not data: return go.Figure()
        
        # NODE DEFINITIONS
        # Indices:
        # 0: Revenue, 1: Gross Profit, 2: Cost of Revenue
        # 3: Operating Profit, 4: R&D, 5: SG&A, 6: Other OpEx
        # 7: Net Income, 8: Tax, 9: Interest
        
        labels = [
            f"Revenue<br>{Visualizer._fmt(data['Revenue'])}",           # 0
            f"Gross Profit<br>{Visualizer._fmt(data['Gross Profit'])}", # 1
            f"Cost of Rev<br>{Visualizer._fmt(data['COGS'])}",          # 2
            f"Op Profit<br>{Visualizer._fmt(data['Operating Profit'])}",# 3
            f"R&D<br>{Visualizer._fmt(data['R&D'])}",                   # 4
            f"SG&A<br>{Visualizer._fmt(data['SG&A'])}",                 # 5
            f"Other OpEx<br>{Visualizer._fmt(data['Other OpEx'])}",     # 6
            f"Net Income<br>{Visualizer._fmt(data['Net Income'])}",     # 7
            f"Tax<br>{Visualizer._fmt(data['Taxes'])}",                 # 8
            f"Interest<br>{Visualizer._fmt(data['Interest'])}"          # 9
        ]
        
        # NODE COLORS (Modeled after Google/Alphabet charts)
        # Revenue=Blue, Profits=Green, Costs=Red
        c_rev = "#4285F4"  # Google Blue
        c_prof = "#34A853" # Google Green
        c_cost = "#EA4335" # Google Red
        c_sub = "#FBBC05"  # Google Yellow (for Interest/Other)
        
        node_colors = [
            c_rev, c_prof, c_cost,  # 0, 1, 2
            c_prof, c_cost, c_cost, c_cost, # 3, 4, 5, 6
            c_prof, c_cost, c_sub   # 7, 8, 9
        ]

        # LINK DEFINITIONS
        source = []
        target = []
        value = []
        link_color = []
        
        # Helper function to add colored links
        def add_link(src, tgt, val, type="neutral"):
            if val > 0:
                source.append(src)
                target.append(tgt)
                value.append(val)
                # Semi-transparent link colors
                if type == "profit": link_color.append("rgba(52, 168, 83, 0.4)") # Green alpha
                elif type == "cost": link_color.append("rgba(234, 67, 53, 0.4)") # Red alpha
                else: link_color.append("rgba(66, 133, 244, 0.3)") # Blue alpha

        # 1. Revenue -> Gross Profit (Profit) & COGS (Cost)
        add_link(0, 1, data['Gross Profit'], "profit")
        add_link(0, 2, data['COGS'], "cost")
        
        # 2. Gross Profit -> Op Profit (Profit) & OpEx (Costs)
        add_link(1, 3, data['Operating Profit'], "profit")
        # OpEx Breakdown
        add_link(1, 4, data['R&D'], "cost")
        add_link(1, 5, data['SG&A'], "cost")
        add_link(1, 6, data['Other OpEx'], "cost")
        
        # 3. Op Profit -> Net Income (Profit) & Tax/Interest (Costs)
        add_link(3, 7, data['Net Income'], "profit")
        add_link(3, 8, data['Taxes'], "cost")
        add_link(3, 9, data['Interest'], "cost")

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20, thickness=20,
                line=dict(color="white", width=0.5),
                label=labels,
                color=node_colors,
                hovertemplate='%{label}<extra></extra>' # Clean hover
            ),
            link=dict(
                source=source, target=target, value=value,
                color=link_color
            )
        )])
        
        fig.update_layout(
            title_text=f"<b>Income Statement Flow</b> {title_suffix}", 
            font_size=13, height=600,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig

    @staticmethod
    def plot_waterfall(data, title_suffix=""):
        if not data: return go.Figure()
        
        # Waterfall with consistent color logic
        vals = [
            data['Revenue'], -data['COGS'], data['Gross Profit'], 
            -data['R&D'], -data['SG&A'], -data['Other OpEx'],
            data['Operating Profit'], -data['Taxes'], -data['Interest'], data['Net Income']
        ]
        
        names = [
            "Revenue", "COGS", "Gross Profit", 
            "R&D", "SG&A", "Other OpEx", 
            "Op Profit", "Tax", "Interest", "Net Income"
        ]
        
        # Bar coloring: Totals=Blue (or Green), Minus=Red, Plus=Green
        measure = ["absolute", "relative", "total", "relative", "relative", "relative", "total", "relative", "relative", "total"]
        
        fig = go.Figure(go.Waterfall(
            name="Income", orientation="v",
            measure=measure,
            x=names,
            y=vals,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#EA4335"}}, # Red
            increasing={"marker": {"color": "#34A853"}}, # Green
            totals={"marker": {"color": "#34A853"}}      # Green (Profit)
        ))

        fig.update_layout(title=f"<b>Profit & Loss Waterfall</b> {title_suffix}", height=600)
        return fig

    @staticmethod
    def plot_sentiment(recommendations):
        """(No changes needed)"""
        try:
            if recommendations.empty: return None
            rec_counts = recommendations.iloc[:, 0:4].sum()
            fig = go.Figure(data=[go.Bar(x=rec_counts.index, y=rec_counts.values)])
            fig.update_layout(title="Analyst Recommendations", height=300)
            return fig
        except: return None



class PDFReport(FPDF):
    """Rozszerzona klasa FPDF do obsługi Markdown i Unicode."""
    def header(self):
        try:
            # Próbujemy ustawić DejaVu
            self.set_font('DejaVu', '', 10)
        except RuntimeError:
            # Jeśli DejaVu nie istnieje, używamy Arial (standardowa, zawsze dostępna)
            self.set_font('Arial', '', 10)
            
        self.cell(0, 10, 'AI Report', 0, 1, 'R')
        self.ln(5)

    def chapter_title(self, label):
        try:
            self.set_font('DejaVu', 'B', 14)
        except RuntimeError:
            self.set_font('Arial', 'B', 14)
            
        self.cell(0, 10, label, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, text):
        try:
            self.set_font('DejaVu', '', 11)
        except RuntimeError:
            self.set_font('Arial', '', 11)
            
        self.multi_cell(0, 6, text)
        self.ln()

class ReportGenerator:
    """Generowanie raportów PDF i analizy AI (Perplexity API) z cytowaniami."""
    
    @staticmethod
    def ensure_font_exists():
        """Pobiera czcionkę DejaVuSans.ttf jeśli nie istnieje."""
        font_path = "DejaVuSans.ttf"
        if not os.path.exists(font_path):
            url = "https://github.com/reingart/pyfpdf/raw/master/fpdf/font/DejaVuSans.ttf"
            try:
                urllib.request.urlretrieve(url, font_path)
            except:
                pass 
        return font_path

    @staticmethod
    def clean_text(text):
        """Kompleksowe czyszczenie tekstu z niebezpiecznych znaków Unicode i naprawa sklejonych słów."""
        if not isinstance(text, str):
            return str(text)
            
        replacements = {
            # --- NAPRAWA SKLEJONYCH SŁÓW (Wehaircutthisby) ---
            '\u200b': ' ',   # Zero-width space -> ZAMIENIAMY NA SPACJĘ (kluczowe!)
            '\xa0': ' ',     # Non-breaking space -> spacja
            
            # --- NAPRAWA DZIWNYCH GWIAZDEK ---
            '∗': '*',        # Operator matematyczny -> zwykła gwiazdka
            '\u2217': '*',   # To samo (kod unicode)
            
            # --- STANDARDOWE ZAMIENNIKI ---
            '\u2013': '-', '\u2014': '-', '\u2011': '-',
            '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
            '\u2022': '*', '\u2026': '...', 
            '\u2248': '~', '\u2260': '!=', '\u2264': '<=', '\u2265': '>=',
            '\u2191': '^', '\u2193': 'v', '\u2192': '->',
            '€': 'EUR', '£': 'GBP', '¥': 'JPY',
        }
        
        for char, repl in replacements.items():
            text = text.replace(char, repl)
            
        # Dodatkowa naprawa: spacja po kropce, jeśli jej brakuje (np. "share.We")
        # Ale tylko jeśli po kropce jest duża litera
        import re
        text = re.sub(r'\.(?=[A-Z])', '. ', text)
        
        # Usuwanie podwójnych spacji
        while '  ' in text:
            text = text.replace('  ', ' ')
            
        try:
            return text.encode('latin-1', 'replace').decode('latin-1')
        except:
            return text

    # ... (metody generate_ai_prompt i get_ai_analysis bez zmian - skopiuj je z poprzedniej wersji) ...
    @staticmethod
    def generate_ai_prompt(ticker, data, info):
        # SKOPIUJ Z POPRZEDNIEJ WERSJI
        revenue = data.get('Revenue', 0)
        net_income = data.get('Net Income', 0)
        gross_profit = data.get('Gross Profit', 0)
        gross_margin = (gross_profit / revenue * 100) if revenue else 0
        
        # Pobieranie waluty (jeśli dostępna, domyślnie USD)
        currency = info.get('currency', 'USD')
        # --- POPRAWKA ---
        # 1. Cena jest w 'info', a nie w 'data'.
        # 2. Używamy standardowych kluczy yfinance.
        current_price = info.get('currentPrice')
        
        # Zabezpieczenie (fallback): jeśli nie ma 'currentPrice', szukaj 'regularMarketPrice' lub 'previousClose'
        if not current_price:
            current_price = info.get('regularMarketPrice') or info.get('previousClose') or 0

        prompt = f"""
       Przygotuj obszerny, profesjonalny EQUITY RESEARCH REPORT o spółce: {ticker} w języku angielskim.

ROLA:
Jesteś starszym analitykiem (Senior Equity Analyst) w banku inwestycyjnym Tier-1 (np. Goldman Sachs, Morgan Stanley). Twój styl pisania musi być "instytucjonalny": zwięzły, oparty na danych, nastawiony na wnioski inwestycyjne (actionable insights), a nie na opowiadanie historii.

DANE FUNDAMENTALNE (WSAD):

Przychody (LTM): {revenue:,.0f} {currency}

Zysk Netto (LTM): {net_income:,.0f} {currency}

Marża Brutto: {gross_margin:.2f}%

P/E Ratio: {info.get('trailingPE', 'N/A')}

Debt/Equity: {info.get('debtToEquity', 'N/A')}

PEG Ratio: {info.get('pegRatio', 'N/A')}

STRUKTURA RAPORTU (Ściśle zachowaj kolejność i formatowanie):

1. INVESTMENT THESIS 

Masthead (Nagłówek): Stwórz tabelę na samej górze z kluczowymi danymi:

Rating (np. BUY / HOLD / SELL - wyróżnione)

Price Target (Cena docelowa)

Current Price  {current_price} {currency}

Implied Upside/Downside (%)

Risk Profile (np. High/Medium)

Investment Thesis: To jest najważniejsza sekcja. Nie pisz "wstępu". Od razu podaj główne argumenty za rekomendacją. Dlaczego teraz? Co rynek przeoczył? (Max 3-4 mocne akapity).

Catalyst Watch: Krótka lista z datami (np. nadchodzące wyniki, decyzje regulacyjne, premiery produktów), które mogą ruszyć kursem w najbliższych 6 miesiącach.

2. FINANCIAL ESTIMATES & SUMMARY (Tabela prognoz)

Zamiast ściany tekstu, stwórz tabelę Markdown "Financial Summary Estimates" prognozującą wyniki na 3 lata w przód (np. 2026E, 2027E, 2028E). Uwzględnij: Revenue, EBITDA, EPS, P/E Ratio, FCF Yield.

Pod tabelą krótki komentarz analityczny dotyczący dynamiki wzrostu i dźwigni operacyjnej.

3. VALUATION (Szczegółowa wycena)

Metodologia: Zastosuj podejście hybrydowe (DCF + Multiples).

SOTP Table (Sum-of-the-Parts): Jeśli spółka ma różne segmenty, KONIECZNIE stwórz tabelę SOTP wyceniającą każdy segment osobno (np. Segment A x Multiple + Segment B x Multiple = Enterprise Value). Jeśli SOTP nie pasuje, zrób tabelę "Valuation Matrix" pokazującą implikowaną cenę przy różnych założeniach WACC i Terminal Growth.

Krótkie uzasadnienie przyjętych mnożników (dlaczego taki P/E lub EV/EBITDA?).

4. SCENARIUSZE CENOWE (Bull / Base / Bear)
Zamiast opisów, przedstaw to w formie tabeli lub listy z przypisanym prawdopodobieństwem:

Bull Case ($XXX): Co musi się udać perfekcyjnie? (np. szybsza adopcja produktu, wzrost marży). Prawdopodobieństwo (np. 20%).

Base Case ($XXX): Twój główny scenariusz. Prawdopodobieństwo (np. 50%).

Bear Case ($XXX): Co pójdzie nie tak? (np. recesja, utrata klienta). Prawdopodobieństwo (np. 30%).

5. KEY RISKS (Ryzyka inwestycyjne)

Konkretne i punktowe (np. ryzyko regulacyjne, koncentracja klientów, ryzyko walutowe). Unikaj ogólników typu "ryzyko rynkowe".

6. SEGMENT ANALYSIS (Analiza operacyjna)

Krótki przegląd wyników per segment/geografia.

Skup się na rentowności i trendach (np. "Segment X rośnie o 20% r/r, ale marże spadają").

7. APPENDIX & DISCLOSURES

Dodaj profesjonalną notkę prawną (Disclaimer) na końcu: "For sophisticated investors only. This report is for educational purposes and does not constitute financial advice."

Analyst Certification: Oświadczenie, że opinie są własne.

WYMAGANIA TECHNICZNE:

Język raportu: Angielski (Profesjonalny żargon finansowy).

Formatowanie: Używaj Markdown do tworzenia tabel, pogrubień i nagłówków.

Styl: "Bottom-line up front" (wnioski na początku). Używaj strony czynnej.

Nie cytuj dosłownie, parafrazuj i syntezuj. 
        """
        return prompt

    @staticmethod
    def get_ai_analysis(api_key, prompt):
        # SKOPIUJ Z POPRZEDNIEJ WERSJI
        try:
            client = openai.OpenAI(
                api_key=api_key, 
                base_url="https://api.perplexity.ai"
            )
            response = client.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10000
            )
            content = response.choices[0].message.content
            citations = getattr(response, 'citations', [])
            return content, citations
        except Exception as e:
            return f"❌ Błąd API: {str(e)}", []
    @staticmethod
    def draw_professional_table(pdf, table_data, title="", col_widths=None, max_width=190):
        """
        Rysuje profesjonalną tabelę w PDF z zawijaniem tekstu i automatycznym dostosowaniem.
        
        Args:
            pdf: Obiekt FPDF
            table_data: Lista list (pierwsza = nagłówek, reszta = wiersze)
            title: Opcjonalny tytuł tabeli
            col_widths: Lista szerokości kolumn. Jeśli None, oblicza automatycznie.
            max_width: Maksymalna dostępna szerokość (domyślnie 190mm)
        """
        
        if not table_data or len(table_data) == 0:
            return
            
        # Konwersja wszystkich danych do stringów i czyszczenie
        table_data = [[ReportGenerator.clean_text(str(cell)) for cell in row] for row in table_data]
        
        num_cols = len(table_data[0])
        num_rows = len(table_data)
        
        # --- KROK 1: Automatyczne obliczanie szerokości kolumn ---
        if col_widths is None:
            col_widths = [max_width / num_cols] * num_cols  # Domyślnie równa szerokość
        else:
            # Normalizuj do całkowitej szerokości max_width
            total = sum(col_widths)
            col_widths = [(w / total) * max_width for w in col_widths]
        
        # --- KROK 2: Sprawdź czy tabela zmieści się na stronie ---
        required_height = ReportGenerator._estimate_table_height(
            table_data, col_widths, font_size=9
        )
        
        # Jeśli brakuje miejsca, dodaj nową stronę
        if pdf.get_y() + required_height > pdf.h - pdf.b_margin:
            pdf.add_page()
        
        # --- KROK 3: Rysuj tytuł (opcjonalnie) ---
        if title:
            pdf.set_font('DejaVu', 'B', 11)
            pdf.cell(0, 8, title, 0, 1, 'L')
            pdf.ln(2)
        
        # --- KROK 4: Rysuj nagłówek ---
        y_start = pdf.get_y()
        header = table_data[0]
        row_height = ReportGenerator._draw_table_row(
            pdf, header, col_widths, 
            font_size=9, 
            is_header=True, 
            bg_color=(200, 200, 200)
        )
        
        # --- KROK 5: Rysuj wiersze danych ---
        for i, row in enumerate(table_data[1:]):
            # Pad row if needed
            while len(row) < num_cols:
                row.append("")
            
            # Zmiennie kolory rzędów (zebra stripe dla lepszej czytelności)
            bg_color = (245, 245, 245) if i % 2 == 0 else (255, 255, 255)
            
            row_height = ReportGenerator._draw_table_row(
                pdf, row, col_widths, 
                font_size=9, 
                is_header=False, 
                bg_color=bg_color
            )
        
        pdf.ln(4)
    
    @staticmethod
    def _draw_table_row(pdf, cells, col_widths, font_size=9, is_header=False, bg_color=None):
        """
        Rysuje pojedynczy wiersz tabeli z Multi-cell zawijaniem.
        Zwraca wysokość wiersza.
        """
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # Ustaw font
        font_style = 'B' if is_header else ''
        pdf.set_font('DejaVu', font_style, font_size)
        
        # Krok 1: Oblicz wysokość wiersza (maksymalna z wszystkich kolumn)
        line_heights = []
        for i, text in enumerate(cells):
            col_w = col_widths[i]
            x, y = pdf.get_x(), pdf.get_y()
            
            # Tymczasowe multi_cell do obliczenia wysokości
            pdf.multi_cell(col_w, 5, text, border=0)
            new_y = pdf.get_y()
            
            height = new_y - y
            line_heights.append(height)
            pdf.set_xy(x, y)
        
        row_height = max(line_heights) if line_heights else 5
        
        # Krok 2: Rysuj tło i obramowanie
        x = x_start
        for i, col_w in enumerate(col_widths):
            if bg_color:
                pdf.set_fill_color(*bg_color)
                pdf.rect(x, y_start, col_w, row_height, 'FD')
            else:
                pdf.rect(x, y_start, col_w, row_height)
            x += col_w
        
        # Krok 3: Wpisz tekst do komórek
        x = x_start
        for i, text in enumerate(cells):
            col_w = col_widths[i]
            pdf.set_xy(x, y_start + 1)
            
            # Wyrównanie: nagłówek do środka, dane do lewej
            align = 'C' if is_header else 'L'
            pdf.multi_cell(col_w, 5, text, border=0, align=align)
            
            x += col_w
        
        # Ustaw pozycję na koniec wiersza
        pdf.set_xy(x_start, y_start + row_height)
        
        return row_height
    
    @staticmethod
    def _estimate_table_height(table_data, col_widths, font_size=9):
        """Estymuje wysokość tabeli (przybliżenie dla sprawdzenia czy zmieści się na stronie)."""
        # Prosta heurystyka: 6 px na linię tekstu + marża
        num_rows = len(table_data)
        avg_height_per_row = 15  # pixels
        return num_rows * avg_height_per_row + 10  # +10 dla marginesu


    
    @staticmethod
    def create_pdf(ticker, analysis_text, metrics, citations=[]):
        # 1. Przygotowanie fontów i czyszczenie tekstu
            font_path = ReportGenerator.ensure_font_exists()
            analysis_text = ReportGenerator.clean_text(analysis_text)
            
            pdf = PDFReport()
            font_loaded = False
            try:
                pdf.add_font('DejaVu', '', font_path, uni=True)
                pdf.add_font('DejaVu', 'B', font_path, uni=True)
                font_loaded = True
            except: pass
            
            pdf.add_page()
            
            # Funkcja pomocnicza do ustawiania fontu
            def set_safe_font(family, style, size):
                try:
                    if font_loaded and family == 'DejaVu': pdf.set_font('DejaVu', style, size)
                    else: pdf.set_font('Arial', style, size)
                except: pdf.set_font('Arial', style, size)
    
            # --- NOWA FUNKCJA: Drukowanie z obsługą **POGRUBIENIA** ---
            def print_formatted_text(text):
                """
                Parsuje tekst:
                - Zamienia **tekst** na pogrubienie
                - Usuwa znaki _ (kursywa), bo nie mamy załadowanego fontu Italic
                - Używa pdf.write() zamiast multi_cell() dla płynnego tekstu
                """
                # Usuwamy kursywę (podłogi), żeby nie śmieciły (DejaVu w tym kodzie nie ma załadowanego stylu 'I')
                text = text.replace('_', '')
                
                # Dzielimy tekst po znaczniku pogrubienia '**'
                # Co drugi element tablicy będzie tym, który ma być pogrubiony
                parts = text.split('**')
                
                for i, part in enumerate(parts):
                    if i % 2 == 1:
                        # Nieparzyste indeksy to tekst wewnątrz **...** -> POGRUBIAMY
                        set_safe_font('DejaVu', 'B', 11)
                        pdf.write(5, part)
                    else:
                        # Parzyste to zwykły tekst
                        set_safe_font('DejaVu', '', 11)
                        pdf.write(5, part)
                
                # Na koniec akapitu przejście do nowej linii + odstęp
                pdf.ln(6)
    
            # --- FUNKCJA RYSUJĄCA WIERSZ TABELI ---
            def draw_table_row(cells, col_widths, is_header=False):
                if is_header: set_safe_font('DejaVu', 'B', 9)
                else: set_safe_font('DejaVu', '', 9)
    
                # KROK 1: Obliczanie wysokości (Symulacja na biało)
                pdf.set_text_color(255, 255, 255)
                original_auto_page_break = pdf.auto_page_break
                pdf.set_auto_page_break(False)
                
                line_heights = []
                sim_y_start = pdf.get_y()
                sim_x_start = pdf.l_margin
                
                for i, text in enumerate(cells):
                    col_w = col_widths[i] if i < len(col_widths) else (190 / len(cells))
                    pdf.set_xy(sim_x_start, sim_y_start)
                    y_before = pdf.get_y()
                    pdf.multi_cell(col_w, 5, str(text), border=0)
                    y_after = pdf.get_y()
                    line_heights.append(y_after - y_before)
                    sim_x_start += col_w
    
                pdf.set_text_color(0, 0, 0) # Powrót do czarnego
                pdf.set_auto_page_break(original_auto_page_break, margin=10)
                pdf.set_xy(pdf.l_margin, sim_y_start)
    
                row_height = max(line_heights) if line_heights else 5
                row_height = max(row_height, 5)
    
                if pdf.get_y() + row_height > pdf.h - 15:
                    pdf.add_page()
                    if is_header: set_safe_font('DejaVu', 'B', 9)
                    else: set_safe_font('DejaVu', '', 9)
    
                # KROK 2: Rysowanie
                y_start = pdf.get_y()
                x_start = pdf.l_margin
                
                for i, text in enumerate(cells):
                    col_w = col_widths[i] if i < len(col_widths) else (190 / len(cells))
                    pdf.set_xy(x_start, y_start)
                    pdf.rect(x_start, y_start, col_w, row_height)
                    align_mode = 'C' if is_header else 'L'
                    pdf.multi_cell(col_w, 5, str(text), border=0, align=align_mode)
                    x_start += col_w
    
                pdf.set_xy(pdf.l_margin, y_start + row_height)
    
            # ---------------------------------------------------------
            # BUDOWANIE RAPORTU
            # ---------------------------------------------------------
            
            set_safe_font('DejaVu', 'B', 16)
            pdf.cell(0, 10, txt=f"AI Investment Report: {ticker}", ln=1, align='C')
            pdf.ln(5)
            
            pdf.set_fill_color(240, 240, 240)
            if metrics:
                pdf.rect(10, pdf.get_y(), 190, 20, 'F')
                set_safe_font('DejaVu', '', 10)
                pdf.set_y(pdf.get_y() + 5)
                col_width = 190 / max(1, len(metrics))
                for k, v in metrics.items():
                    clean_k = ReportGenerator.clean_text(str(k))
                    clean_v = ReportGenerator.clean_text(str(v))
                    if not font_loaded:
                        clean_k = clean_k.encode('latin-1', 'ignore').decode('latin-1')
                        clean_v = clean_v.encode('latin-1', 'ignore').decode('latin-1')
                    pdf.cell(col_width, 10, f"{clean_k}: {clean_v}", 0, 0, 'C')
                pdf.ln(20)
    
            set_safe_font('DejaVu', '', 11)
            lines = analysis_text.split('\n')
            in_table = False
            table_header = []
            table_rows = []
    
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Tabela
                if line.startswith('|'):
                    in_table = True
                    cells = [ReportGenerator.clean_text(c.strip()) for c in line.split('|')]
                    if cells and cells[0] == '': cells.pop(0)
                    if cells and cells[-1] == '': cells.pop(-1)
                    
                    if '---' in line: continue
                    if not table_header: table_header = cells
                    else: table_rows.append(cells)
                    continue
                
                if (in_table and not line.startswith('|')) or (in_table and i == len(lines)-1):
                    in_table = False
                    if table_header:
                        pdf.ln(2)
                        num_cols = len(table_header)
                        col_w = 190 / max(1, num_cols)
                        col_widths = [col_w] * num_cols
                        draw_table_row(table_header, col_widths, is_header=True)
                        for row in table_rows:
                            while len(row) < num_cols: row.append("")
                            draw_table_row(row[:num_cols], col_widths, is_header=False)
                        pdf.ln(5)
                    table_header = []
                    table_rows = []
                    set_safe_font('DejaVu', '', 11)
    
                if not line:
                    if not in_table: pdf.ln(2)
                    continue
                if in_table: continue
    
                if not font_loaded:
                    line = line.encode('latin-1', 'replace').decode('latin-1')
    
                # --- RENDEROWANIE TREŚCI ---
                if line.startswith('#'):
                    set_safe_font('DejaVu', 'B', 12)
                    pdf.cell(0, 8, line.lstrip('#').strip(), 0, 1)
                    set_safe_font('DejaVu', '', 11)
                    
                elif line.startswith('- ') or line.startswith('* '):
                    # Listy punktowane
                    bullet = chr(149) if font_loaded else "-"
                    pdf.set_x(15)
                    # Tu też używamy nowej funkcji do formatowania treści punktu
                    pdf.write(5, bullet + " ")
                    print_formatted_text(line[2:])
                    
                else:
                    # Zwykły akapit z obsługą BOLD (**)
                    print_formatted_text(line)
            if citations:
                pdf.add_page()
                set_safe_font('DejaVu', 'B', 14)
                pdf.cell(0, 10, "Sources", 0, 1)
                set_safe_font('DejaVu', '', 10)
                
                for i, link in enumerate(citations, 1):
                    clean_link = ReportGenerator.clean_text(link)
                    if not font_loaded:
                        clean_link = clean_link.encode('latin-1', 'ignore').decode('latin-1')
                    
                    # Użycie write() zamiast multi_cell() dla płynnego zawijania
                    pdf.write(6, f"[{i}] {clean_link}")
                    pdf.ln(8) # Odstęp po każdym linku

            return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- MAIN APPLICATION LOGIC ---
def main():
    st.title("🧩 fin.sankey | Financial Flow Visualizer")
    st.markdown("Cash flow visualization for NASDAQ/S&P500 companies")

    # --- STATE MANAGEMENT (SESSION STATE) ---
    # 1. State for Main Ticker
    if 'rev_change' not in st.session_state: st.session_state['rev_change'] = 0
    if 'cost_change' not in st.session_state: st.session_state['cost_change'] = 0
    
    # 2. State for Benchmark (Competitor)
    if 'comp_rev_change' not in st.session_state: st.session_state['comp_rev_change'] = 0
    if 'comp_cost_change' not in st.session_state: st.session_state['comp_cost_change'] = 0

    # Reset callbacks
    def reset_main_sliders():
        st.session_state['rev_change'] = 0
        st.session_state['cost_change'] = 0

    def reset_comp_sliders():
        st.session_state['comp_rev_change'] = 0
        st.session_state['comp_cost_change'] = 0

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("Configuration")
        
        # Get ticker list
        tickers_list = DataManager.get_tickers_list()
        
        # --- MAIN SECTION ---
        st.subheader("1. Main Company")
        selected_item = st.selectbox(
            "Search for a company:",
            options=tickers_list,
            index=0
        )
        ticker_input = selected_item.split(" | ")[0]
        
        # What-If for Main
        st.caption(f"Simulation: {ticker_input}")
        rev_change = st.slider("Revenue Change (%)", -30, 30, key='rev_change')
        cost_change = st.slider("Cost Change (%)", -30, 30, key='cost_change')
        st.button("↺ Reset (Main)", on_click=reset_main_sliders)
        
        st.markdown("---")
        
        # --- BENCHMARK SECTION ---
        st.subheader("2. Benchmark (Competitor)")
        enable_benchmark = st.checkbox("Compare with Competitor")
        ticker_comp = None
        
        # Initialize competitor variables to 0 to prevent crashes
        comp_rev_change = 0
        comp_cost_change = 0
        
        if enable_benchmark:
            selected_comp = st.selectbox(
                "Select Competitor:",
                options=tickers_list,
                index=1 if len(tickers_list) > 1 else 0,
                key="benchmark_select"
            )
            ticker_comp = selected_comp.split(" | ")[0]
            
            # What-If for Competitor
            st.caption(f"Simulation: {ticker_comp}")
            comp_rev_change = st.slider("Rev Change (Comp) %", -30, 30, key='comp_rev_change')
            comp_cost_change = st.slider("Cost Change (Comp) %", -30, 30, key='comp_cost_change')
            st.button("↺ Reset (Benchmark)", on_click=reset_comp_sliders)

    if not ticker_input:
        st.info("Select a company from the list to start.")
        return

    # Fetch data for main ticker
    data_mgr = DataManager()
    data_dict = data_mgr.get_financials(ticker_input)
    
    if not data_dict:
        return 

    # Process data for MAIN (with sliders)
    sankey_vals = data_mgr.extract_sankey_data(
        data_dict['income_stmt'], 
        revenue_mod=1 + (rev_change/100), 
        cost_mod=1 + (cost_change/100)
    )

    # --- MAIN TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Viz & Benchmark", "📈 Metrics Dashboard", "🤖 AI Report", "📑 Extra Data"])

    with tab1:
        # Layout logic: Check if benchmark mode is on
        show_benchmark = enable_benchmark and ticker_comp
        
        if show_benchmark:
            # If benchmark active -> split screen
            col1, col2 = st.columns(2)
        else:
            # If benchmark off -> full width container
            col1 = st.container()
            col2 = None

        # DRAW MAIN CHART (Always in col1)
        with col1:
            st.subheader(f"Analysis: {ticker_input}")
            
            # --- ADDED SAFETY CHECK ---
            if sankey_vals.get('Revenue', 0) <= 0 and sankey_vals.get('OpEx_Total', 0) <= 0:
                st.warning(f"⚠️ Company {ticker_input} reports no revenue or significant costs (likely SPAC or holding). Sankey chart cannot be generated.")
            else:
                # Old code drawing charts
                if rev_change != 0 or cost_change != 0:
                    st.caption(f"Simulation: Rev {rev_change:+}%, Cost {cost_change:+}%")
                    
                fig_sankey = Visualizer.plot_sankey(sankey_vals, title_suffix=f"({ticker_input})")
                st.plotly_chart(fig_sankey, use_container_width=True, key="sankey_main")
                
                fig_water = Visualizer.plot_waterfall(sankey_vals, title_suffix=f"({ticker_input})")
                st.plotly_chart(fig_water, use_container_width=True, key="water_main")

        # DRAW BENCHMARK (Only if show_benchmark is True)
        if show_benchmark:
            with col2:
                st.subheader(f"Benchmark: {ticker_comp}")
                comp_data = data_mgr.get_financials(ticker_comp)
                
                if comp_data:
                    if comp_rev_change != 0 or comp_cost_change != 0:
                        st.caption(f"Simulation: Rev {comp_rev_change:+}%, Cost {comp_cost_change:+}%")
                    
                    comp_vals = data_mgr.extract_sankey_data(
                        comp_data['income_stmt'],
                        revenue_mod=1 + (comp_rev_change/100),
                        cost_mod=1 + (comp_cost_change/100)
                    )
                    
                    fig_sankey_comp = Visualizer.plot_sankey(comp_vals, title_suffix=f"({ticker_comp})")
                    st.plotly_chart(fig_sankey_comp, use_container_width=True, key="sankey_comp")
                    
                    fig_water_comp = Visualizer.plot_waterfall(comp_vals, title_suffix=f"({ticker_comp})")
                    st.plotly_chart(fig_water_comp, use_container_width=True, key="water_comp")
                else:
                    st.warning("No data found for the comparison ticker.")


    with tab2:
        st.subheader("📊 Metrics Dashboard")
        
        # --- Data Preparation ---
        info = data_dict.get("info", {}) or {}
        bs = data_dict.get("balance_sheet", None)
        
        # Helper Formatters
        def fmt_num(val, suffix="", compact=False):
            if val is None: return "N/A"
            try:
                val = float(val)
                # Jeśli flaga compact=True, skracamy duże liczby
                if compact:
                    if val >= 1e12: return f"{val/1e12:.2f}T{suffix}"
                    if val >= 1e9: return f"{val/1e9:.2f}B{suffix}"
                    if val >= 1e6: return f"{val/1e6:.2f}M{suffix}"
                # Domyślne formatowanie dla mniejszych wskaźników (np. EPS, P/E)
                return f"{val:,.2f}{suffix}"
            except: return "N/A"

        def fmt_pct(val):
            if val is None: return "N/A"
            try: return f"{float(val)*100:.2f}%"
            except: return "N/A"
            
        def safe_div(a, b):
            try:
                return float(a) / float(b) if b else None
            except: return None

        # Calculations for custom metrics
        total_assets = None
        total_equity = None
        if bs is not None and not bs.empty:
            # Try finding Total Assets
            for k in ["Total Assets", "Total assets"]:
                if k in bs.index:
                    total_assets = float(bs.loc[k].iloc[0])
                    break
            # Try finding Total Equity
            for k in ["Total Stockholder Equity", "Total Equity", "Stockholders Equity"]:
                if k in bs.index:
                    total_equity = float(bs.loc[k].iloc[0])
                    break
        
        shares = info.get("sharesOutstanding")
        debt = info.get("totalDebt")
        rev = info.get("totalRevenue")
        empl = info.get("fullTimeEmployees")
        
        assets_per_share = safe_div(total_assets, shares)
        debt_to_assets = safe_div(debt, total_assets)
        debt_to_capital = safe_div(debt, (debt + total_equity) if (debt and total_equity) else None)
        rev_per_empl = safe_div(rev, empl)

        # --- CSS STYLING FOR CARDS ---
        st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: #262730;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #464b5c;
        }
        </style>
        """, unsafe_allow_html=True)

        # ==============================================================================
        # SECTION 1: KEY HIGHLIGHTS
        # ==============================================================================
        st.markdown("#### 🔹 Key Highlights")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Revenue per Share", fmt_num(info.get("revenuePerShare")))
        k2.metric("EPS (Trailing)", fmt_num(info.get("trailingEps")))
        k3.metric("ROE", fmt_pct(info.get("returnOnEquity")))
        k4.metric("ROIC", "N/A", help="Requires manual calculation (NOPAT/InvestedCapital)") 

        k1b, k2b, k3b, k4b = st.columns(4)
        k1b.metric("Debt / Equity", fmt_num(info.get("debtToEquity")))
        k2b.metric("Book Value / Share", fmt_num(info.get("bookValue")))
        k3b.metric("Current Ratio", fmt_num(info.get("currentRatio")))
        k4b.metric("Quick Ratio", fmt_num(info.get("quickRatio")))

        st.divider()

        # ==============================================================================
        # SECTION 2: VALUATION
        # ==============================================================================
        st.markdown("#### 💲 Valuation")
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Price / Sales (P/S)", fmt_num(info.get("priceToSalesTrailing12Months")))
        w2.metric("Price / Earnings (P/E)", fmt_num(info.get("trailingPE")))
        w3.metric("Price / Book (P/B)", fmt_num(info.get("priceToBook")))
        w4.metric("PEG Ratio", fmt_num(info.get("pegRatio")))

        w1b, w2b, w3b, w4b = st.columns(4)
        w1b.metric("EV / Revenue", fmt_num(info.get("enterpriseToRevenue")))
        w2b.metric("EV / EBITDA", fmt_num(info.get("enterpriseToEbitda")))
        w3b.metric("Market Cap", fmt_num(info.get("marketCap"), suffix=" $", compact=True))
        w4b.metric("Forward P/E", fmt_num(info.get("forwardPE")))

        st.divider()

        # ==============================================================================
        # SECTION 3: FINANCIAL HEALTH (SOLVENCY)
        # ==============================================================================
        st.markdown("#### 🏦 Financial Health")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Total Assets / Share", fmt_num(assets_per_share))
        f2.metric("Debt / Assets", fmt_num(debt_to_assets))
        f3.metric("Debt / Total Capital", fmt_num(debt_to_capital))
        f4.metric("Revenue / Employee", fmt_num(rev_per_empl))
        
        st.divider()

        # ==============================================================================
        # SECTION 4: PROFITABILITY
        # ==============================================================================
        st.markdown("#### 📈 Profitability")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Gross Margin", fmt_pct(info.get("grossMargins")))
        r2.metric("Operating Margin", fmt_pct(info.get("operatingMargins")))
        r3.metric("Profit Margin", fmt_pct(info.get("profitMargins")))
        r4.metric("Beta (Volatility)", fmt_num(info.get("beta")))

    with tab3:
        st.header("🤖 AI Report (Perplexity Sonar)")
        st.caption("This analysis combines fundamental data with the latest web news (Live Search).")
        
        # --- KONFIGURACJA API (BEZPOŚREDNIO W KODZIE) ---
        # Wklej tutaj swój klucz Perplexity zaczynający się od 'pplx-...'
        PERPLEXITY_API_KEY = "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"  
        
        # Sprawdzenie czy mamy dane finansowe
        if not sankey_vals:
            st.warning("Insufficient financial data to generate the report.")
        else:
            # Generowanie Promptu (teraz ukryte dla użytkownika)
            prompt = ReportGenerator.generate_ai_prompt(ticker_input, sankey_vals, data_dict['info'])
            
            # Przycisk Generowania
            generate_btn = st.button("🚀 Generate Live Report", type="primary")
            
            # Session State
            if "ai_report_content" not in st.session_state:
                st.session_state["ai_report_content"] = None
            
            # --- LOGIKA PRZYCISKU ---
            if generate_btn:
                # Proste sprawdzenie czy klucz nie jest domyślny
                if "TUTAJ" in PERPLEXITY_API_KEY:
                    st.error("⚠️ Error: Developer did not configure the API Key in the source code.")
                else:
                    with st.spinner("⏳ Perplexity is searching the web and analyzing data..."):
                        # Wywołanie API (zwraca teraz krotkę: tekst, lista_cytowań)
                        analysis_text, citations = ReportGenerator.get_ai_analysis(PERPLEXITY_API_KEY, prompt)
                        
                        # Zapisanie wyniku do sesji jako słownik
                        st.session_state["ai_report_data"] = {
                            "text": analysis_text,
                            "citations": citations
                        }
            
            # --- WYŚWIETLANIE WYNIKU (JEŚLI ISTNIEJE W SESJI) ---
            if "ai_report_data" in st.session_state and st.session_state["ai_report_data"]:
                report_data = st.session_state["ai_report_data"]
                
                st.markdown("### 📝 Analysis Result")
                st.markdown(report_data["text"])
                
                # Wyświetlenie listy źródeł (jeśli są dostępne)
                if report_data["citations"]:
                    st.divider()
                    st.markdown("#### 📚 Sources / Citations")
                    for i, link in enumerate(report_data["citations"], 1):
                        st.markdown(f"**[{i}]** [{link}]({link})")
                
                st.divider()
                
                # Przygotowanie danych do PDF
                rev = sankey_vals.get('Revenue', 1)
                net = sankey_vals.get('Net Income', 0)
                metrics_for_pdf = {
                    "Ticker": ticker_input,
                    "P/E Ratio": str(info.get("trailingPE", "N/A")),
                    "Revenue": f"${rev:,.0f}",
                    "Net Income": f"${net:,.0f}"
                }
                
                # Generowanie pliku PDF (przekazujemy też cytowania)
                pdf_bytes = ReportGenerator.create_pdf(
                    ticker_input, 
                    report_data["text"], # Nie usuwamy gwiazdek markdown, bo nowa klasa PDF je obsłuży
                    metrics_for_pdf,
                    citations=report_data["citations"]
                )
                
                st.download_button(
                    label="📄 Download Professional PDF Report",
                    data=pdf_bytes,
                    file_name=f"{ticker_input}_Perplexity_Report.pdf",
                    mime="application/pdf"
                )
                            
    with tab4:
        st.header("Additional Data")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Insider Trading")
            insider_df = data_dict['insider']
            if not insider_df.empty:
                st.dataframe(insider_df, use_container_width=True)
            else:
                st.write("No insider trading data available.") 
        with col_b:
            st.subheader("Analyst Sentiment")
            rec_df = data_dict['recommendations']
            if not rec_df.empty:
                st.dataframe(rec_df.tail(10), use_container_width=True)
            else:
                st.write("No analyst recommendations available.")

if __name__ == "__main__":
     main()
