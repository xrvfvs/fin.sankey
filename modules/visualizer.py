# -*- coding: utf-8 -*-
"""
Visualization module for financial charts using Plotly.
"""

import plotly.graph_objects as go


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
        """Plot analyst recommendations sentiment chart."""
        try:
            if recommendations.empty: return None
            rec_counts = recommendations.iloc[:, 0:4].sum()
            fig = go.Figure(data=[go.Bar(x=rec_counts.index, y=rec_counts.values)])
            fig.update_layout(title="Analyst Recommendations", height=300)
            return fig
        except: return None

    @staticmethod
    def _format_financial_value(val):
        """Format value with B/M/K suffix for financial display."""
        if val is None:
            return "N/A"
        abs_val = abs(val)
        sign = "-" if val < 0 else ""
        if abs_val >= 1e9:
            return f"{sign}${abs_val/1e9:.1f}B"
        elif abs_val >= 1e6:
            return f"{sign}${abs_val/1e6:.0f}M"
        elif abs_val >= 1e3:
            return f"{sign}${abs_val/1e3:.0f}K"
        else:
            return f"{sign}${abs_val:,.0f}"

    @staticmethod
    def plot_historical_trend(income_stmt, metrics=None):
        """
        Creates a line chart showing historical trends of key financial metrics.

        Args:
            income_stmt: DataFrame with income statement (columns = periods)
            metrics: List of metrics to plot. If None, uses defaults.
        """
        if income_stmt is None or income_stmt.empty:
            return go.Figure()

        # Default metrics to track
        if metrics is None:
            metrics = [
                ("Total Revenue", "Revenue"),
                ("Gross Profit", "Gross Profit"),
                ("Operating Income", "Operating Income"),
                ("Net Income", "Net Income")
            ]

        fig = go.Figure()

        # Colors for different metrics
        colors = ["#4285F4", "#34A853", "#FBBC05", "#EA4335"]

        all_values = []  # Collect all values to determine scale

        for i, (metric_key, metric_name) in enumerate(metrics):
            # Try to find the metric in the income statement
            if metric_key in income_stmt.index:
                values = income_stmt.loc[metric_key].values
                all_values.extend(values)

                # Format dates for x-axis (reverse to show oldest first)
                dates = []
                for col in income_stmt.columns:
                    if hasattr(col, 'strftime'):
                        quarter = (col.month - 1) // 3 + 1
                        dates.append(f"{col.year}-Q{quarter}")
                    else:
                        dates.append(str(col))

                # Reverse to show chronological order (oldest to newest)
                dates_rev = dates[::-1]
                values_rev = values[::-1]

                # Format hover values with B/M suffix
                hover_texts = [Visualizer._format_financial_value(v) for v in values_rev]

                fig.add_trace(go.Scatter(
                    x=dates_rev,
                    y=values_rev,
                    name=metric_name,
                    mode='lines+markers',
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=8),
                    hovertemplate=f'{metric_name}: %{{text}}<extra></extra>',
                    text=hover_texts
                ))

        # Determine scale for y-axis labels
        if all_values:
            max_abs = max(abs(v) for v in all_values if v is not None)
            if max_abs >= 1e9:
                divisor, suffix = 1e9, "B"
            elif max_abs >= 1e6:
                divisor, suffix = 1e6, "M"
            else:
                divisor, suffix = 1, ""
        else:
            divisor, suffix = 1, ""

        fig.update_layout(
            title="<b>Historical Financial Trends</b>",
            xaxis_title="Period",
            yaxis_title=f"Value (${suffix})",
            height=400,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=60, r=20, t=60, b=20)
        )

        # Scale y-axis values for cleaner display
        if divisor > 1:
            fig.update_yaxes(
                tickformat=".1f",
                ticksuffix=suffix,
                tickprefix="$"
            )
            # Update trace y-values to be in scaled units
            for trace in fig.data:
                trace.y = [v / divisor if v is not None else None for v in trace.y]

        return fig

    @staticmethod
    def calculate_yoy_metrics(income_stmt):
        """
        Calculates Year-over-Year changes for key metrics.
        Compares most recent period with the previous period (index 0 vs index 1).

        Returns dict with metric name -> (current_value, yoy_change_pct)
        """
        if income_stmt is None or income_stmt.empty:
            return {}

        if len(income_stmt.columns) < 2:
            return {}

        results = {}
        metrics_to_calc = [
            ("Total Revenue", "Revenue"),
            ("Gross Profit", "Gross Profit"),
            ("Operating Income", "Operating Income"),
            ("Net Income", "Net Income")
        ]

        for metric_key, metric_name in metrics_to_calc:
            if metric_key in income_stmt.index:
                current = income_stmt.loc[metric_key].iloc[0]
                # Compare with previous period (index 1 = previous year for annual data)
                previous = income_stmt.loc[metric_key].iloc[1]

                if previous and previous != 0:
                    yoy_change = ((current - previous) / abs(previous)) * 100
                else:
                    yoy_change = None

                results[metric_name] = (current, yoy_change)

        return results
