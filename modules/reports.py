# -*- coding: utf-8 -*-
"""
PDF and AI report generation module.
"""

import os
import json
import datetime
import urllib.request
import re
import openai
from fpdf import FPDF

from config import LOCAL_CACHE_DIR, LOCAL_CACHE_TTL_HOURS


class PDFReport(FPDF):
    """Extended FPDF class for Markdown and Unicode support."""

    font_family = 'Helvetica'  # Default fallback font

    def header(self):
        try:
            self.set_font(PDFReport.font_family, '', 10)
        except Exception:
            self.set_font('Helvetica', '', 10)
        self.cell(0, 10, 'AI Report', 0, 1, 'R')
        self.ln(5)

    def chapter_title(self, label):
        try:
            self.set_font(PDFReport.font_family, 'B', 14)
        except Exception:
            self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, label, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, text):
        try:
            self.set_font(PDFReport.font_family, '', 11)
        except Exception:
            self.set_font('Helvetica', '', 11)
        self.multi_cell(0, 6, text)
        self.ln()


class ReportGenerator:
    """AI report and PDF generation with Perplexity API and caching."""

    CACHE_DIR = LOCAL_CACHE_DIR
    CACHE_TTL_HOURS = LOCAL_CACHE_TTL_HOURS

    @staticmethod
    def _get_cache_path(ticker):
        """Returns the cache file path for a given ticker."""
        os.makedirs(ReportGenerator.CACHE_DIR, exist_ok=True)
        return os.path.join(ReportGenerator.CACHE_DIR, f"{ticker}_report.json")

    @staticmethod
    def get_cached_report(ticker):
        """
        Returns cached report if it exists and is not expired.
        Returns tuple: (report_data, cache_age_hours) or (None, None)
        """
        cache_path = ReportGenerator._get_cache_path(ticker)

        if not os.path.exists(cache_path):
            return None, None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check cache age
            cached_time = datetime.datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            age = datetime.datetime.now() - cached_time
            age_hours = age.total_seconds() / 3600

            if age_hours > ReportGenerator.CACHE_TTL_HOURS:
                return None, None  # Cache expired

            return cache_data.get('report'), age_hours
        except Exception:
            return None, None

    @staticmethod
    def save_report_to_cache(ticker, report_data):
        """Saves report data to cache file."""
        cache_path = ReportGenerator._get_cache_path(ticker)

        try:
            cache_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'ticker': ticker,
                'report': report_data
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def ensure_font_exists():
        """Downloads DejaVuSans.ttf if it doesn't exist."""
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
        """Comprehensive text cleaning from dangerous Unicode characters and fixing merged words."""
        if not isinstance(text, str):
            return str(text)

        replacements = {
            # --- FIX MERGED WORDS ---
            '\u200b': '',    # Zero-width space -> remove
            '\u200c': '',    # Zero-width non-joiner
            '\u200d': '',    # Zero-width joiner
            '\ufeff': '',    # BOM / zero-width no-break space
            '\xa0': ' ',     # Non-breaking space -> space

            # --- FIX WEIRD ASTERISKS ---
            '∗': '*',        # Mathematical operator -> regular asterisk
            '\u2217': '*',   # Same (unicode code)

            # --- STANDARD REPLACEMENTS ---
            '\u2013': '-', '\u2014': '-', '\u2011': '-',
            '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
            '\u2022': '*', '\u2026': '...',
            '\u2248': '~', '\u2260': '!=', '\u2264': '<=', '\u2265': '>=',
            '\u2191': '^', '\u2193': 'v', '\u2192': '->',
            '€': 'EUR', '£': 'GBP', '¥': 'JPY',
        }

        for char, repl in replacements.items():
            text = text.replace(char, repl)

        # Remove other zero-width and invisible Unicode characters
        text = re.sub(r'[\u200b-\u200f\u2028-\u202f\u2060-\u206f]', '', text)

        # Additional fix: space after period if missing (e.g. "share.We")
        text = re.sub(r'\.(?=[A-Z])', '. ', text)

        # Fix $X.XXvalue -> $X.XX value (numbers merged with words)
        text = re.sub(r'(\$[\d,.]+)([a-zA-Z])', r'\1 \2', text)

        # Remove double spaces
        text = re.sub(r' +', ' ', text)

        try:
            return text.encode('latin-1', 'replace').decode('latin-1')
        except:
            return text

    @staticmethod
    def generate_ai_prompt(ticker, data, info):
        """Generate the AI analysis prompt for Perplexity API."""
        revenue = data.get('Revenue', 0)
        net_income = data.get('Net Income', 0)
        gross_profit = data.get('Gross Profit', 0)
        gross_margin = (gross_profit / revenue * 100) if revenue else 0

        # Get currency (if available, default USD)
        currency = info.get('currency', 'USD')
        current_price = info.get('currentPrice')

        # Fallback: if no 'currentPrice', look for 'regularMarketPrice' or 'previousClose'
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
        """Call Perplexity API to generate AI analysis."""
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
            return f"Error API: {str(e)}", []

    @staticmethod
    def create_pdf(ticker, analysis_text, metrics, citations=[]):
        """Create PDF report from analysis text."""
        # 1. Prepare fonts and clean text
        font_path = ReportGenerator.ensure_font_exists()
        analysis_text = ReportGenerator.clean_text(analysis_text)

        # Reset font to default before trying to load DejaVu
        PDFReport.font_family = 'Helvetica'

        pdf = PDFReport()
        font_loaded = False
        try:
            if os.path.exists(font_path):
                pdf.add_font('DejaVu', '', font_path, uni=True)
                pdf.add_font('DejaVu', 'B', font_path, uni=True)
                font_loaded = True
                PDFReport.font_family = 'DejaVu'
        except Exception:
            font_loaded = False
            PDFReport.font_family = 'Helvetica'

        pdf.add_page()

        # Helper function to set font safely
        def set_safe_font(family, style, size):
            try:
                if font_loaded and family == 'DejaVu':
                    pdf.set_font('DejaVu', style, size)
                else:
                    pdf.set_font('Helvetica', style, size)
            except Exception:
                pdf.set_font('Helvetica', style, size)

        # --- NEW FUNCTION: Print with **BOLD** support ---
        def print_formatted_text(text):
            """
            Parses text:
            - Replaces **text** with bold
            - Removes _ characters (italic), as we don't have Italic font loaded
            - Uses pdf.write() instead of multi_cell() for flowing text
            """
            # Remove italic markers (underscores)
            text = text.replace('_', '')

            # Split text by bold marker '**'
            # Every other element in the array will be bold
            parts = text.split('**')

            for i, part in enumerate(parts):
                if i % 2 == 1:
                    # Odd indices are text inside **...** -> BOLD
                    set_safe_font('DejaVu', 'B', 11)
                    pdf.write(5, part)
                else:
                    # Even indices are regular text
                    set_safe_font('DejaVu', '', 11)
                    pdf.write(5, part)

            # End of paragraph - newline + spacing
            pdf.ln(6)

        # --- FUNCTION TO DRAW TABLE ROW ---
        def draw_table_row(cells, col_widths, is_header=False):
            if is_header: set_safe_font('DejaVu', 'B', 9)
            else: set_safe_font('DejaVu', '', 9)

            # STEP 1: Calculate height (White text simulation)
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

            pdf.set_text_color(0, 0, 0)  # Back to black
            pdf.set_auto_page_break(original_auto_page_break, margin=10)
            pdf.set_xy(pdf.l_margin, sim_y_start)

            row_height = max(line_heights) if line_heights else 5
            row_height = max(row_height, 5)

            if pdf.get_y() + row_height > pdf.h - 15:
                pdf.add_page()
                if is_header: set_safe_font('DejaVu', 'B', 9)
                else: set_safe_font('DejaVu', '', 9)

            # STEP 2: Drawing
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
        # BUILD REPORT
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

            # Table
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

            # --- CONTENT RENDERING ---
            if line.startswith('#'):
                set_safe_font('DejaVu', 'B', 12)
                pdf.cell(0, 8, line.lstrip('#').strip(), 0, 1)
                set_safe_font('DejaVu', '', 11)

            elif line.startswith('- ') or line.startswith('* '):
                # Bulleted lists
                bullet = chr(149) if font_loaded else "-"
                pdf.set_x(15)
                # Use new function to format bullet content
                pdf.write(5, bullet + " ")
                print_formatted_text(line[2:])

            else:
                # Regular paragraph with BOLD (**) support
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

                # Use write() instead of multi_cell() for smooth wrapping
                pdf.write(6, f"[{i}] {clean_link}")
                pdf.ln(8)  # Spacing after each link

        # fpdf2 returns bytearray directly, no need to encode
        return bytes(pdf.output())
