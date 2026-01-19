# -*- coding: utf-8 -*-
"""
Financial Sankey - Cash flow visualization for NASDAQ/S&P500 companies.

Main application entry point.
"""

import os
import streamlit as st
import pandas as pd

# Import from modules
from modules.utils import convert_df_to_excel, convert_multiple_df_to_excel
from modules.auth import SupabaseAuth
from modules.data_manager import DataManager
from modules.visualizer import Visualizer
from modules.reports import ReportGenerator
from modules.theme import init_theme, apply_theme_css, render_theme_toggle, get_current_theme
from modules.i18n import init_language, t, render_language_selector
from modules.news import render_news_feed, get_market_sentiment_from_news


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="san.key - Advanced Financial Viz",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- MAIN APPLICATION LOGIC ---
def main():
    # Initialize theme and language
    init_theme()
    init_language()

    # Apply theme CSS
    apply_theme_css()

    st.title(t('app_title'))
    st.markdown(t('app_subtitle'))

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
        # --- USER AUTH SECTION ---
        if SupabaseAuth.is_configured():
            # Initialize session state for auth
            if "user" not in st.session_state:
                st.session_state["user"] = None
            if "auth_mode" not in st.session_state:
                st.session_state["auth_mode"] = "login"  # or "register"

            # Restore Supabase session on each run
            SupabaseAuth.restore_session()

            current_user = st.session_state.get("user")

            if current_user:
                # User is logged in
                st.success(f"Welcome, {current_user.email}!")
                if st.button("Logout", use_container_width=True):
                    SupabaseAuth.sign_out()
                    st.session_state["user"] = None
                    st.rerun()

                # Show user stats
                watchlist = SupabaseAuth.get_watchlist(current_user.id)
                saved = SupabaseAuth.get_saved_analyses(current_user.id)
                st.caption(f"Watchlist: {len(watchlist)} | Saved analyses: {len(saved)}")
                st.markdown("---")
            else:
                # Login/Register forms
                auth_tab1, auth_tab2 = st.tabs([t('login'), t('register')])

                with auth_tab1:
                    with st.form("login_form"):
                        login_email = st.text_input("Email", key="login_email")
                        login_password = st.text_input("Password", type="password", key="login_pass")
                        login_submit = st.form_submit_button("Login", use_container_width=True)

                        if login_submit:
                            if login_email and login_password:
                                result = SupabaseAuth.sign_in(login_email, login_password)
                                if result.get("success"):
                                    st.session_state["user"] = result["user"]
                                    st.success("Logged in successfully!")
                                    st.rerun()
                                else:
                                    st.error(result.get("error", "Login failed"))
                            else:
                                st.warning("Please enter email and password")

                with auth_tab2:
                    with st.form("register_form"):
                        reg_email = st.text_input("Email", key="reg_email")
                        reg_password = st.text_input("Password", type="password", key="reg_pass")
                        reg_password2 = st.text_input("Confirm Password", type="password", key="reg_pass2")
                        reg_submit = st.form_submit_button("Create Account", use_container_width=True)

                        if reg_submit:
                            if not reg_email or not reg_password:
                                st.warning("Please fill all fields")
                            elif reg_password != reg_password2:
                                st.error("Passwords don't match")
                            elif len(reg_password) < 6:
                                st.error("Password must be at least 6 characters")
                            else:
                                result = SupabaseAuth.sign_up(reg_email, reg_password)
                                if result.get("success"):
                                    st.success("Account created! Please check your email to confirm.")
                                else:
                                    st.error(result.get("error", "Registration failed"))

                st.markdown("---")

        # --- SETTINGS SECTION (Theme & Language) ---
        with st.expander(t('settings'), expanded=False):
            render_language_selector()
            st.markdown("---")
            render_theme_toggle()

        st.markdown("---")

        st.header(t('configuration'))

        # Get ticker list
        tickers_list = DataManager.get_tickers_list()

        # --- MAIN SECTION ---
        st.subheader(t('main_company'))

        # Show user's watchlist if logged in
        current_user = st.session_state.get("user")
        if current_user and SupabaseAuth.is_configured():
            watchlist = SupabaseAuth.get_watchlist(current_user.id)
            if watchlist:
                watchlist_tickers = [f"{w['ticker']} | {w.get('company_name', '')}" for w in watchlist]
                st.caption(t('your_watchlist'))
                selected_from_watchlist = st.selectbox(
                    t('quick_select'),
                    options=[""] + watchlist_tickers,
                    key="watchlist_select"
                )
                if selected_from_watchlist:
                    # Find matching item in tickers_list
                    ticker_from_wl = selected_from_watchlist.split(" | ")[0]
                    matching = [t for t in tickers_list if t.startswith(ticker_from_wl)]
                    if matching:
                        default_idx = tickers_list.index(matching[0])
                    else:
                        default_idx = 0
                else:
                    default_idx = 0
            else:
                default_idx = 0
        else:
            default_idx = 0

        selected_item = st.selectbox(
            "Search for a company:",
            options=tickers_list,
            index=default_idx
        )
        ticker_input = selected_item.split(" | ")[0]
        company_name = selected_item.split(" | ")[1] if " | " in selected_item else ticker_input

        # Add to watchlist button (if logged in)
        if current_user and SupabaseAuth.is_configured():
            user_watchlist_tickers = [w['ticker'] for w in SupabaseAuth.get_watchlist(current_user.id)]
            watchlist_limit = SupabaseAuth.can_add_to_watchlist(current_user.id)

            if ticker_input in user_watchlist_tickers:
                if st.button("Remove from Watchlist", key="remove_wl"):
                    if SupabaseAuth.remove_from_watchlist(current_user.id, ticker_input):
                        st.success(f"Removed {ticker_input} from watchlist!")
                        st.rerun()
                    else:
                        st.error("Failed to remove from watchlist")
            else:
                # Check watchlist limit
                can_add = watchlist_limit.get('allowed', True)
                if not can_add:
                    st.warning(f"⚠️ {watchlist_limit.get('message', 'Watchlist full')}")

                if st.button("Add to Watchlist", key="add_wl", disabled=not can_add):
                    result = SupabaseAuth.add_to_watchlist(current_user.id, ticker_input, company_name)
                    if result.get("success"):
                        st.success(f"Added {ticker_input} to watchlist!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result.get('error', 'Unknown error')}")

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

    # --- PERIOD SELECTION (after data is loaded) ---
    # Get available periods for dropdown
    available_periods = DataManager.get_available_periods(data_dict['income_stmt'])

    # Check historical periods limit based on user tier
    current_user_periods = st.session_state.get("user")
    periods_limit = None  # None = unlimited
    is_guest = False

    if current_user_periods and SupabaseAuth.is_configured():
        periods_limit = SupabaseAuth.get_historical_periods_limit(current_user_periods.id)
    else:
        # Guest users get Free tier limits
        is_guest = True
        periods_limit = SupabaseAuth.TIER_LIMITS['free']['historical_periods']

    # Apply limit to available periods if needed
    if periods_limit is not None and available_periods and len(available_periods) > periods_limit:
        limited_periods = available_periods[:periods_limit]
        periods_limited = True
    else:
        limited_periods = available_periods
        periods_limited = False

    # Add period selector to sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("3. Reporting Period")
        if limited_periods:
            period_options = [p[0] for p in limited_periods]
            selected_period_name = st.selectbox(
                "Select period for analysis:",
                options=period_options,
                index=0,
                help="Choose which quarterly report to analyze"
            )
            # Find the index for the selected period
            selected_period_index = next(
                (p[1] for p in limited_periods if p[0] == selected_period_name), 0
            )
            # Show upgrade hint if periods are limited
            if periods_limited:
                if is_guest:
                    st.caption(f"🔒 Guest: {periods_limit} periods. Login for more.")
                else:
                    st.caption(f"🔒 Free tier: {periods_limit} periods. Upgrade for more.")
        else:
            selected_period_index = 0
            st.info("No historical periods available")

    # Process data for MAIN (with selected period and sliders)
    sankey_vals = data_mgr.extract_sankey_data(
        data_dict['income_stmt'],
        period_index=selected_period_index,
        revenue_mod=1 + (rev_change/100),
        cost_mod=1 + (cost_change/100)
    )

    info = data_dict.get("info", {}) or {}

    # --- MAIN TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([t('tab_viz'), t('tab_metrics'), t('tab_ai_report'), t('tab_extra')])

    with tab1:
        render_tab_visualization(data_mgr, data_dict, ticker_input, sankey_vals, rev_change, cost_change,
                                  enable_benchmark, ticker_comp, comp_rev_change, comp_cost_change)

    with tab2:
        render_tab_metrics(data_dict, sankey_vals, info)

    with tab3:
        render_tab_ai_report(ticker_input, sankey_vals, info, data_dict)

    with tab4:
        render_tab_extra_data(ticker_input, data_dict)


def render_tab_visualization(data_mgr, data_dict, ticker_input, sankey_vals, rev_change, cost_change,
                              enable_benchmark, ticker_comp, comp_rev_change, comp_cost_change):
    """Render Tab 1: Visualization & Benchmark."""
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

    # --- HISTORICAL TRENDS SECTION ---
    st.divider()
    st.subheader("📈 Historical Trends")

    # Plot historical trend chart
    fig_trend = Visualizer.plot_historical_trend(data_dict['income_stmt'])
    st.plotly_chart(fig_trend, use_container_width=True, key="historical_trend")

    # YoY metrics table
    yoy_metrics = Visualizer.calculate_yoy_metrics(data_dict['income_stmt'])
    if yoy_metrics:
        st.markdown("#### Year-over-Year Changes")
        yoy_cols = st.columns(len(yoy_metrics))
        for i, (metric_name, (current_val, yoy_change)) in enumerate(yoy_metrics.items()):
            with yoy_cols[i]:
                # Format current value (handle negative values properly)
                abs_val = abs(current_val)
                sign = "-" if current_val < 0 else ""

                if abs_val >= 1e9:
                    formatted_val = f"{sign}${abs_val/1e9:.1f}B"
                elif abs_val >= 1e6:
                    formatted_val = f"{sign}${abs_val/1e6:.0f}M"
                elif abs_val >= 1e3:
                    formatted_val = f"{sign}${abs_val/1e3:.0f}K"
                else:
                    formatted_val = f"{sign}${abs_val:,.0f}"

                # Format YoY change with color indicator
                if yoy_change is not None:
                    delta_str = f"{yoy_change:+.1f}%"
                else:
                    delta_str = None

                st.metric(
                    label=metric_name,
                    value=formatted_val,
                    delta=delta_str
                )


def render_tab_metrics(data_dict, sankey_vals, info):
    """Render Tab 2: Metrics Dashboard."""
    st.subheader("📊 Metrics Dashboard")

    # --- Data Preparation ---
    bs = data_dict.get("balance_sheet", None)

    # Helper Formatters
    def fmt_num(val, suffix="", compact=False):
        if val is None: return "N/A"
        try:
            val = float(val)
            if compact:
                if val >= 1e12: return f"{val/1e12:.2f}T{suffix}"
                if val >= 1e9: return f"{val/1e9:.2f}B{suffix}"
                if val >= 1e6: return f"{val/1e6:.2f}M{suffix}"
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
    total_debt_bs = None
    cash = None

    if bs is not None and not bs.empty:
        # Try finding Total Assets
        for k in ["Total Assets", "Total assets"]:
            if k in bs.index:
                total_assets = float(bs.loc[k].iloc[0])
                break
        # Try finding Total Equity
        for k in ["Total Stockholder Equity", "Total Equity", "Stockholders Equity", "Stockholders' Equity"]:
            if k in bs.index:
                total_equity = float(bs.loc[k].iloc[0])
                break
        # Try finding Total Debt from balance sheet
        for k in ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"]:
            if k in bs.index:
                total_debt_bs = float(bs.loc[k].iloc[0])
                break
        # Try finding Cash
        for k in ["Cash And Cash Equivalents", "Cash", "Cash Cash Equivalents And Short Term Investments"]:
            if k in bs.index:
                cash = float(bs.loc[k].iloc[0])
                break

    # --- ROIC Calculation ---
    roic = None
    income_stmt = data_dict.get("income_stmt")

    if income_stmt is not None and not income_stmt.empty:
        # Get Operating Income
        operating_income = None
        for k in ["Operating Income", "EBIT"]:
            if k in income_stmt.index:
                operating_income = float(income_stmt.loc[k].iloc[0])
                break

        # Calculate effective tax rate
        tax_rate = None
        pretax_income = None
        tax_provision = None

        for k in ["Pretax Income", "Income Before Tax"]:
            if k in income_stmt.index:
                pretax_income = float(income_stmt.loc[k].iloc[0])
                break

        for k in ["Tax Provision", "Income Tax Expense"]:
            if k in income_stmt.index:
                tax_provision = float(income_stmt.loc[k].iloc[0])
                break

        if pretax_income and pretax_income != 0 and tax_provision is not None:
            tax_rate = tax_provision / pretax_income
            tax_rate = max(0, min(0.5, tax_rate))
        else:
            tax_rate = 0.21  # Default US corporate tax rate

        # Calculate NOPAT
        if operating_income is not None:
            nopat = operating_income * (1 - tax_rate)

            # Calculate Invested Capital
            total_debt_val = total_debt_bs if total_debt_bs else info.get("totalDebt", 0) or 0
            equity_val = total_equity or 0
            cash_val = cash or 0

            invested_capital = equity_val + total_debt_val - cash_val

            if invested_capital and invested_capital > 0:
                roic = nopat / invested_capital

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

    # SECTION 1: KEY HIGHLIGHTS
    st.markdown("#### 🔹 Key Highlights")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Revenue per Share", fmt_num(info.get("revenuePerShare")))
    k2.metric("EPS (Trailing)", fmt_num(info.get("trailingEps")))
    k3.metric("ROE", fmt_pct(info.get("returnOnEquity")))
    k4.metric("ROIC", fmt_pct(roic), help="Return on Invested Capital = NOPAT / (Equity + Debt - Cash)")

    k1b, k2b, k3b, k4b = st.columns(4)
    k1b.metric("Debt / Equity", fmt_num(info.get("debtToEquity")))
    k2b.metric("Book Value / Share", fmt_num(info.get("bookValue")))
    k3b.metric("Current Ratio", fmt_num(info.get("currentRatio")))
    k4b.metric("Quick Ratio", fmt_num(info.get("quickRatio")))

    st.divider()

    # SECTION 2: VALUATION
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

    # SECTION 3: FINANCIAL HEALTH (SOLVENCY)
    st.markdown("#### 🏦 Financial Health")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Total Assets / Share", fmt_num(assets_per_share))
    f2.metric("Debt / Assets", fmt_num(debt_to_assets))
    f3.metric("Debt / Total Capital", fmt_num(debt_to_capital))
    f4.metric("Revenue / Employee", fmt_num(rev_per_empl))

    st.divider()

    # SECTION 4: PROFITABILITY
    st.markdown("#### 📈 Profitability")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Gross Margin", fmt_pct(info.get("grossMargins")))
    r2.metric("Operating Margin", fmt_pct(info.get("operatingMargins")))
    r3.metric("Profit Margin", fmt_pct(info.get("profitMargins")))
    r4.metric("Beta (Volatility)", fmt_num(info.get("beta")))


def render_tab_ai_report(ticker_input, sankey_vals, info, data_dict):
    """Render Tab 3: AI Report."""
    st.header("🤖 AI Report (Perplexity Sonar)")
    st.caption("This analysis combines fundamental data with the latest web news (Live Search).")

    # --- API CONFIGURATION ---
    PERPLEXITY_API_KEY = None

    try:
        if "PERPLEXITY_API_KEY" in st.secrets:
            PERPLEXITY_API_KEY = st.secrets["PERPLEXITY_API_KEY"]
    except Exception:
        pass

    if not PERPLEXITY_API_KEY:
        PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")

    api_key_ready = PERPLEXITY_API_KEY and len(PERPLEXITY_API_KEY) >= 10

    if not sankey_vals:
        st.warning("Insufficient financial data to generate the report.")
    elif not api_key_ready:
        st.error("AI Reports are currently unavailable. Please contact the administrator.")
    else:
        # Generate Prompt
        prompt = ReportGenerator.generate_ai_prompt(ticker_input, sankey_vals, data_dict['info'])

        # --- CHECK CACHE ---
        current_user = st.session_state.get("user")
        user_id = current_user.id if current_user else None

        # 1. Check Supabase caches (global + user saved)
        supabase_cached = None
        if SupabaseAuth.is_configured():
            supabase_cached = SupabaseAuth.get_best_cached_report(ticker_input, user_id)

        # 2. Check local file cache as fallback
        local_cached, local_cache_age = ReportGenerator.get_cached_report(ticker_input)

        # Determine best cache source
        cached_report = None
        cache_source = None

        if supabase_cached:
            cached_report = supabase_cached
            cache_source = supabase_cached.get("from_cache", "global")
            if cache_source == "global":
                age_info = f"{supabase_cached.get('age_days', 0)} days old"
            else:
                age_info = "from your saved analyses"
        elif local_cached:
            cached_report = local_cached
            cache_source = "local"
            cache_hours = int(local_cache_age)
            cache_minutes = int((local_cache_age - cache_hours) * 60)
            age_info = f"{cache_hours}h {cache_minutes}m old"

        # --- CHECK AI REPORT LIMIT ---
        ai_limit_info = None
        can_generate = True
        guest_blocked = False

        if not current_user:
            # Guest users cannot generate AI reports
            can_generate = False
            guest_blocked = True
            st.warning("🔒 Login required to generate AI reports. Create a free account to get started!")
        elif SupabaseAuth.is_configured():
            ai_limit_info = SupabaseAuth.can_generate_ai_report(current_user.id)
            can_generate = ai_limit_info.get('allowed', True)

            # Show usage info
            used = ai_limit_info.get('used', 0)
            limit = ai_limit_info.get('limit')
            tier = ai_limit_info.get('tier', 'free')

            if limit is not None:
                remaining = limit - used
                if remaining > 0:
                    st.caption(f"📊 AI Reports: {used}/{limit} used this month ({tier.upper()} tier)")
                else:
                    st.warning(f"⚠️ {ai_limit_info.get('message', 'Limit reached')}")
            else:
                st.caption(f"📊 AI Reports: Unlimited ({tier.upper()} tier)")

        # Show cache info
        if cached_report:
            if cache_source == "global":
                st.info(f"🌐 Global cached report available ({age_info}) - saves API costs!")
            elif cache_source == "user_saved":
                st.info(f"👤 Found in your saved analyses")
            else:
                st.info(f"💾 Local cached report available ({age_info})")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                use_cache_btn = st.button("📂 Load Cached Report", type="secondary")
            with btn_col2:
                generate_btn = st.button("🚀 Generate New Report", type="primary", disabled=not can_generate)
        else:
            generate_btn = st.button("🚀 Generate Live Report", type="primary", disabled=not can_generate)
            use_cache_btn = False

        # Session State
        if "ai_report_content" not in st.session_state:
            st.session_state["ai_report_content"] = None

        # --- CACHE LOGIC ---
        if use_cache_btn and cached_report:
            if cached_report.get("text"):
                cached_report["text"] = ReportGenerator.clean_text(cached_report["text"])
            st.session_state["ai_report_data"] = cached_report
            st.toast(f"✅ Loaded from {cache_source} cache!", icon="💾")

        # --- GENERATE BUTTON LOGIC ---
        if generate_btn:
            with st.spinner("⏳ Perplexity is searching the web and analyzing data..."):
                analysis_text, citations = ReportGenerator.get_ai_analysis(PERPLEXITY_API_KEY, prompt)

                # Clean text immediately after API response
                analysis_text = ReportGenerator.clean_text(analysis_text)

                report_data = {
                    "text": analysis_text,
                    "citations": citations
                }
                st.session_state["ai_report_data"] = report_data

                # Save to LOCAL cache
                ReportGenerator.save_report_to_cache(ticker_input, report_data)

                # Save to GLOBAL Supabase cache (if logged in)
                if current_user and SupabaseAuth.is_configured():
                    financial_snapshot = {
                        "revenue": sankey_vals.get('Revenue', 0),
                        "net_income": sankey_vals.get('Net Income', 0),
                        "pe_ratio": info.get("trailingPE")
                    }
                    if SupabaseAuth.save_to_global_cache(ticker_input, analysis_text, citations, financial_snapshot):
                        st.toast("✅ Report saved to global cache!", icon="🌐")
                    else:
                        st.toast("✅ Report saved locally", icon="💾")

                    # INCREMENT AI REPORT USAGE COUNTER
                    SupabaseAuth.increment_ai_report_usage(current_user.id)

        # --- DISPLAY RESULT ---
        if "ai_report_data" in st.session_state and st.session_state["ai_report_data"]:
            report_data = st.session_state["ai_report_data"]

            # Clean the text before display
            display_text = ReportGenerator.clean_text(report_data["text"]) if report_data.get("text") else ""

            # Escape $ signs to prevent LaTeX interpretation
            display_text = display_text.replace("$", "\\$")

            st.markdown("### 📝 Analysis Result")
            st.markdown(display_text)

            # Display sources
            if report_data["citations"]:
                st.divider()
                st.markdown("#### 📚 Sources / Citations")
                for i, link in enumerate(report_data["citations"], 1):
                    st.markdown(f"**[{i}]** [{link}]({link})")

            st.divider()

            # Prepare PDF data
            rev = sankey_vals.get('Revenue', 1)
            net = sankey_vals.get('Net Income', 0)
            metrics_for_pdf = {
                "Ticker": ticker_input,
                "P/E Ratio": str(info.get("trailingPE", "N/A")),
                "Revenue": f"${rev:,.0f}",
                "Net Income": f"${net:,.0f}"
            }

            # Generate PDF
            pdf_bytes = ReportGenerator.create_pdf(
                ticker_input,
                report_data["text"],
                metrics_for_pdf,
                citations=report_data["citations"]
            )

            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                # Check export permission for PDF
                current_user_for_export = st.session_state.get("user")
                can_export_pdf = False
                is_guest_export = False

                if current_user_for_export and SupabaseAuth.is_configured():
                    export_info = SupabaseAuth.can_export(current_user_for_export.id)
                    can_export_pdf = export_info.get('allowed', True)
                else:
                    is_guest_export = True
                    can_export_pdf = SupabaseAuth.TIER_LIMITS['free']['export_enabled']

                if can_export_pdf:
                    st.download_button(
                        label="📄 Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"{ticker_input}_Perplexity_Report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.button("📄 Download PDF Report", disabled=True, use_container_width=True)
                    if is_guest_export:
                        st.caption("🔒 Login & upgrade to Pro to export PDFs")
                    else:
                        st.caption("🔒 Upgrade to Pro to export PDFs")

            with dl_col2:
                # Save to account (if logged in)
                current_user = st.session_state.get("user")
                if current_user and SupabaseAuth.is_configured():
                    save_limit = SupabaseAuth.can_save_analysis(current_user.id)
                    can_save = save_limit.get('allowed', True)

                    if not can_save:
                        st.warning(f"⚠️ {save_limit.get('message', 'Limit reached')}")

                    if st.button("💾 Save to My Analyses", use_container_width=True, key="save_analysis", disabled=not can_save):
                        financial_data = {
                            "revenue": sankey_vals.get('Revenue', 0),
                            "net_income": sankey_vals.get('Net Income', 0),
                            "pe_ratio": info.get("trailingPE"),
                        }
                        if SupabaseAuth.save_analysis(
                            current_user.id,
                            ticker_input,
                            report_data["text"],
                            report_data.get("citations"),
                            financial_data
                        ):
                            st.success("Analysis saved to your account!")
                        else:
                            st.error("Failed to save analysis")
                else:
                    st.info("Login to save analyses to your account")


def render_tab_extra_data(ticker_input, data_dict):
    """Render Tab 4: Extra Data."""
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
            # Display sentiment chart
            sentiment_fig = Visualizer.plot_sentiment(rec_df)
            if sentiment_fig:
                st.plotly_chart(sentiment_fig, use_container_width=True)
            # Display recent recommendations table
            st.dataframe(rec_df.tail(10), use_container_width=True)
        else:
            st.write("No analyst recommendations available.")

    # --- NEWS FEED SECTION ---
    st.divider()
    st.subheader(f"📰 {t('latest_news')}")

    # Get news sentiment
    sentiment = get_market_sentiment_from_news(ticker_input)

    if sentiment.get('status') == 'ok' and sentiment.get('news_count', 0) > 0:
        # Display sentiment summary
        sent_col1, sent_col2, sent_col3, sent_col4 = st.columns(4)
        with sent_col1:
            st.metric(t('positive_news'), sentiment['positive'],
                     delta=f"{sentiment['positive_ratio']*100:.0f}%")
        with sent_col2:
            st.metric(t('negative_news'), sentiment['negative'],
                     delta=f"-{sentiment['negative_ratio']*100:.0f}%" if sentiment['negative'] > 0 else "0%")
        with sent_col3:
            st.metric(t('neutral_news'), sentiment['neutral'])
        with sent_col4:
            score = sentiment['sentiment_score']
            sentiment_label = "🟢 Positive" if score > 0.1 else "🔴 Negative" if score < -0.1 else "🟡 Neutral"
            st.metric(t('news_sentiment'), sentiment_label)

        # Display news feed
        render_news_feed(ticker_input, show_thumbnails=True)
    else:
        st.info(t('no_news_available', ticker=ticker_input))

    # --- EXPORT DATA SECTION ---
    st.divider()
    st.subheader("📥 Export Financial Data")

    # Check export permission for Excel
    current_user_excel = st.session_state.get("user")
    can_export_excel = False
    is_guest_excel = False

    if current_user_excel and SupabaseAuth.is_configured():
        export_info_excel = SupabaseAuth.can_export(current_user_excel.id)
        can_export_excel = export_info_excel.get('allowed', True)
    else:
        is_guest_excel = True
        can_export_excel = SupabaseAuth.TIER_LIMITS['free']['export_enabled']

    if can_export_excel:
        st.write("Download raw financial data for further analysis in Excel.")
    else:
        if is_guest_excel:
            st.warning("🔒 Excel export requires Pro tier. Login & upgrade to export data.")
        else:
            st.warning("🔒 Excel export is available for Pro and Enterprise tiers. Upgrade to export data.")

    export_col1, export_col2, export_col3 = st.columns(3)

    income_stmt = data_dict['income_stmt']
    balance_sheet = data_dict['balance_sheet']
    insider_df = data_dict['insider']
    rec_df = data_dict['recommendations']

    with export_col1:
        if not can_export_excel:
            st.button("📊 Income Statement", disabled=True, help="Upgrade to Pro to export")
        elif income_stmt is not None and not income_stmt.empty:
            income_excel = convert_df_to_excel(income_stmt.T, "Income Statement")
            st.download_button(
                label="📊 Income Statement",
                data=income_excel,
                file_name=f"{ticker_input}_income_statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download full income statement data"
            )
        else:
            st.button("📊 Income Statement", disabled=True, help="No data available")

    with export_col2:
        if not can_export_excel:
            st.button("📋 Balance Sheet", disabled=True, help="Upgrade to Pro to export")
        elif balance_sheet is not None and not balance_sheet.empty:
            balance_excel = convert_df_to_excel(balance_sheet.T, "Balance Sheet")
            st.download_button(
                label="📋 Balance Sheet",
                data=balance_excel,
                file_name=f"{ticker_input}_balance_sheet.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download full balance sheet data"
            )
        else:
            st.button("📋 Balance Sheet", disabled=True, help="No data available")

    with export_col3:
        if not can_export_excel:
            st.button("📦 All Data (Multi-sheet)", disabled=True, help="Upgrade to Pro to export")
        else:
            # Export all data in one file with multiple sheets
            all_data = {
                "Income Statement": income_stmt.T if income_stmt is not None and not income_stmt.empty else pd.DataFrame(),
                "Balance Sheet": balance_sheet.T if balance_sheet is not None and not balance_sheet.empty else pd.DataFrame(),
                "Insider Trading": insider_df if not insider_df.empty else pd.DataFrame(),
                "Recommendations": rec_df if not rec_df.empty else pd.DataFrame()
            }
            # Filter out empty dataframes
            all_data = {k: v for k, v in all_data.items() if not v.empty}

            if all_data:
                all_excel = convert_multiple_df_to_excel(all_data)
                st.download_button(
                    label="📦 All Data (Multi-sheet)",
                    data=all_excel,
                    file_name=f"{ticker_input}_all_financial_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download all available data in one Excel file"
                )
            else:
                st.button("📦 All Data", disabled=True, help="No data available")

    # --- MY SAVED ANALYSES SECTION (for logged-in users) ---
    current_user = st.session_state.get("user")
    if current_user and SupabaseAuth.is_configured():
        st.divider()
        st.subheader("📁 My Saved Analyses")

        saved_analyses = SupabaseAuth.get_saved_analyses(current_user.id)

        if saved_analyses:
            for analysis in saved_analyses:
                with st.expander(f"**{analysis['ticker']}** - {analysis['created_at'][:10]}"):
                    st.markdown(analysis.get('report_text', 'No content')[:500] + "...")

                    if analysis.get('financial_data'):
                        fd = analysis['financial_data']
                        st.caption(f"Revenue: ${fd.get('revenue', 0):,.0f} | Net Income: ${fd.get('net_income', 0):,.0f}")

                    col_view, col_del = st.columns([3, 1])
                    with col_del:
                        if st.button("Delete", key=f"del_{analysis['id']}"):
                            if SupabaseAuth.delete_analysis(current_user.id, analysis['id']):
                                st.success("Analysis deleted!")
                                st.rerun()
        else:
            st.info("No saved analyses yet. Generate an AI report and click 'Save to My Analyses' to save it here.")


if __name__ == "__main__":
    main()
