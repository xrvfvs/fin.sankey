
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 23 13:56:21 2025

@author: rafal
"""

import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from fpdf import FPDF
import datetime

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

class ReportGenerator:
    """Generating PDF reports and AI Prompts."""
    
    @staticmethod
    def generate_ai_prompt(ticker, data, info):
        # Safe value retrieval
        revenue = data.get('Revenue', 0)
        net_income = data.get('Net Income', 0)
        gross_profit = data.get('Gross Profit', 0)
        
        # Calculate margin (safe division)
        gross_margin = (gross_profit / revenue * 100) if revenue else 0
        
        prompt = f"""
        As a fundamental analyst, evaluate the company {ticker} based on the following data:
        - Revenue: ${revenue:,.0f}
        - Net Income: ${net_income:,.0f}
        - Gross Margin: {gross_margin:.2f}%
        - P/E Ratio: {info.get('trailingPE', 'N/A')}
        - Debt/EBITDA: {info.get('debtToEquity', 'N/A')} (proxy via D/E)
        
        Focus on risks (e.g., high COGS, R&D) and potential growth catalysts.
        Format the response using Markdown.
        """
        return prompt

    @staticmethod
    def create_pdf(ticker, analysis_text, metrics):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=f"Financial Report: {ticker}", ln=1, align='C')
        
        # Date
        pdf.set_font("Arial", size=10)
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Generated on: {datetime.date.today()}", ln=1)
        
        # Metrics
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="Key Metrics:", ln=1)
        pdf.set_font("Arial", size=10)
        
        for k, v in metrics.items():
            pdf.cell(200, 8, txt=f"{k}: {v}", ln=1)
            
        # Analysis
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="AI Analysis (Summary):", ln=1)
        pdf.set_font("Arial", size=10)
        
        # Character encoding handling (latin-1 cleanup)
        replacements = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
            'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
        }
        safe_text = analysis_text
        for pl, lat in replacements.items():
            safe_text = safe_text.replace(pl, lat)
            
        safe_text = safe_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=safe_text)
        
        return pdf.output(dest='S').encode('latin-1')

# --- MAIN APPLICATION LOGIC ---
def main():
    st.title("🧩 san.key | Financial Flow Visualizer")
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
        info = data_dict['info']
        met_col1, met_col2, met_col3, met_col4 = st.columns(4)
        met_col1.metric("P/E Ratio", info.get("trailingPE", "N/A"))
        met_col2.metric("Forward P/E", info.get("forwardPE", "N/A"))
        met_col3.metric("PEG Ratio", info.get("pegRatio", "N/A"))
        met_col4.metric("Current Ratio", info.get("currentRatio", "N/A"))
        
        st.markdown("---")
        st.subheader("Valuation Details")
        market_cap = info.get("marketCap")
        ebitda = info.get("ebitda")
        
        st.json({
            "Market Cap": f"${market_cap:,.0f}" if isinstance(market_cap, (int, float)) else market_cap,
            "EBITDA": f"${ebitda:,.0f}" if isinstance(ebitda, (int, float)) else ebitda,
            "Debt to Equity": info.get("debtToEquity"),
            "Free Cash Flow": info.get("freeCashflow")
        })

    with tab3:
        st.header("Generate AI Report")
        
        # Safety Check: Do we have data?
        if not sankey_vals:
            st.warning("Insufficient financial data to generate report.")
        else:
            prompt = ReportGenerator.generate_ai_prompt(ticker_input, sankey_vals, data_dict['info'])
            st.code(prompt, language="markdown")
            
            st.info("Below is a simulation of the AI response:")
            
            # --- SAFETY CHECK ---
            rev = sankey_vals.get('Revenue', 1) # Default 1 to avoid div by zero
            gp = sankey_vals.get('Gross Profit', 0)
            net = sankey_vals.get('Net Income', 0)
            
            margin = (gp / rev) * 100 if rev else 0
            # --------------------
            
            mock_analysis = f"""
            **Company Analysis: {ticker_input}**
            
            1. **Operational Efficiency**: The company shows a gross margin of {margin:.1f}%.
            
            2. **What-If Scenario**: Assuming a revenue change of {rev_change}% and cost change of {cost_change}%,
            estimated Net Income would be ${net:,.0f}.
            
            3. **Risks**: PEG Ratio at {info.get('pegRatio', 'N/A')}.
            """
            st.markdown(mock_analysis)
            
            # PDF Export
            metrics_for_pdf = {
                "P/E": str(info.get("trailingPE", "N/A")),
                "Revenue": f"${rev:,.0f}",
                "Net Income": f"${net:,.0f}"
            }
            
            if st.button("Generate PDF Report"):
                pdf_bytes = ReportGenerator.create_pdf(ticker_input, mock_analysis.replace("*", ""), metrics_for_pdf)
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=f"{ticker_input}_report.pdf",
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
