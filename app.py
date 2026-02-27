"""
Norwegian Loan Calculator – Streamlit Dashboard
================================================
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from norwegian_loan_calculator import (
    LoanParameters,
    RentalParameters,
    compare_loans,
    format_nok,
    TAX_DEDUCTION_RATE,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Norsk Lånekalkulator",
    page_icon="🏠",
    layout="wide",
)

st.title("Norwegian Loan Calculator")
st.markdown("Compare **annuity** and **serial** loans with Norwegian tax deductions & rental income")

# ---------------------------------------------------------------------------
# Sidebar – inputs
# ---------------------------------------------------------------------------
st.sidebar.header("Loan Parameters")

principal = st.sidebar.number_input(
    "Loan amount (NOK)",
    min_value=100_000,
    max_value=50_000_000,
    value=3_500_000,
    step=100_000,
    format="%d",
)

interest_rate = st.sidebar.slider(
    "Annual interest rate (%)",
    min_value=0.5,
    max_value=12.0,
    value=4.5,
    step=0.1,
)

term_years = st.sidebar.slider(
    "Loan term (years)",
    min_value=1,
    max_value=40,
    value=25,
)

monthly_fee = st.sidebar.number_input(
    "Monthly fee / termingebyr (NOK)",
    min_value=0,
    max_value=500,
    value=50,
    step=10,
)

# --- Rental section ---
st.sidebar.markdown("---")
st.sidebar.header("Rental Income")

enable_rental = st.sidebar.checkbox("Include rental income", value=False)

rental = None
if enable_rental:
    monthly_rent = st.sidebar.number_input(
        "Monthly rental income (NOK)",
        min_value=0,
        max_value=100_000,
        value=8_000,
        step=500,
    )

    rental_type = st.sidebar.radio(
        "Rental type",
        options=[
            "Own home (≥50% occupied) – tax-free",
            "Separate unit / full property – taxed",
            "Short-term rental (<30 days) – partially taxed",
        ],
    )

    maintenance = 0
    if rental_type == "Separate unit / full property – taxed":
        maintenance = st.sidebar.number_input(
            "Annual maintenance cost (NOK, deductible)",
            min_value=0,
            max_value=200_000,
            value=15_000,
            step=1_000,
        )

    rental = RentalParameters(
        monthly_rental_income=monthly_rent,
        is_short_term="Short-term" in rental_type,
        owner_occupies_half="Own home" in rental_type,
        annual_maintenance_cost=maintenance,
    )

# ---------------------------------------------------------------------------
# Calculate
# ---------------------------------------------------------------------------
loan = LoanParameters(
    principal=principal,
    annual_interest_rate=interest_rate / 100,
    term_years=term_years,
    extra_fees_per_month=monthly_fee,
)

annuity, serial = compare_loans(loan, rental)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
st.markdown("---")

def delta_str(ann_val: float, ser_val: float) -> str:
    diff = ann_val - ser_val
    if diff > 0:
        return f"Annuity costs {format_nok(diff)} more"
    elif diff < 0:
        return f"Annuity saves {format_nok(abs(diff))}"
    return "Same"

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Annuity – First Payment", format_nok(annuity.monthly_payments[0].total_payment))
    st.metric("Serial – First Payment", format_nok(serial.monthly_payments[0].total_payment))

with col2:
    st.metric("Annuity – Total Interest", format_nok(annuity.total_interest))
    st.metric("Serial – Total Interest", format_nok(serial.total_interest))

with col3:
    st.metric("Annuity – Tax Deduction", format_nok(annuity.total_tax_deduction))
    st.metric("Serial – Tax Deduction", format_nok(serial.total_tax_deduction))

with col4:
    label = "Net Cost After Rental" if enable_rental else "Net Cost"
    ann_val = annuity.total_net_cost_after_rental if enable_rental else annuity.total_net_cost
    ser_val = serial.total_net_cost_after_rental if enable_rental else serial.total_net_cost
    st.metric(f"Annuity – {label}", format_nok(ann_val))
    st.metric(f"Serial – {label}", format_nok(ser_val))

diff = ann_val - ser_val
if diff > 0:
    st.info(f"Serial loan saves you **{format_nok(diff)}** over {term_years} years, "
            f"but starts with a higher monthly payment "
            f"({format_nok(serial.monthly_payments[0].total_payment)} vs "
            f"{format_nok(annuity.monthly_payments[0].total_payment)}).")
elif diff < 0:
    st.info(f"Annuity loan saves you **{format_nok(abs(diff))}** over {term_years} years.")

# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Side-by-Side Comparison")

rows = {
    "Total Paid": (annuity.total_paid, serial.total_paid),
    "Total Interest": (annuity.total_interest, serial.total_interest),
    "Total Fees": (annuity.total_fees, serial.total_fees),
    "Tax Deduction (22%)": (annuity.total_tax_deduction, serial.total_tax_deduction),
    "Net Cost": (annuity.total_net_cost, serial.total_net_cost),
}
if enable_rental:
    rows["Rental Income (gross)"] = (annuity.total_rental_income_gross, serial.total_rental_income_gross)
    rows["Rental Tax"] = (annuity.total_rental_tax, serial.total_rental_tax)
    rows["Rental Income (net)"] = (annuity.total_rental_income_net, serial.total_rental_income_net)
    rows["Net Cost After Rental"] = (annuity.total_net_cost_after_rental, serial.total_net_cost_after_rental)

comp_df = pd.DataFrame(
    {
        "Annuity": [format_nok(v[0]) for v in rows.values()],
        "Serial": [format_nok(v[1]) for v in rows.values()],
        "Difference": [format_nok(v[0] - v[1]) for v in rows.values()],
    },
    index=rows.keys(),
)
st.dataframe(comp_df, width="stretch")

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Charts")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Monthly Payments",
    "Remaining Balance",
    "Interest vs Principal",
    "Cumulative Cost",
    "Annual Net Cost",
    "Rate Sensitivity",
])

months = [mp.month for mp in annuity.monthly_payments]

# --- Tab 1: Monthly payments ---
with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months,
        y=[mp.total_payment for mp in annuity.monthly_payments],
        name="Annuity",
        line=dict(width=2),
    ))
    fig.add_trace(go.Scatter(
        x=months,
        y=[mp.total_payment for mp in serial.monthly_payments],
        name="Serial",
        line=dict(width=2),
    ))
    fig.update_layout(
        title="Monthly Payment Over Time",
        xaxis_title="Month",
        yaxis_title="Payment (NOK)",
        yaxis_tickformat=",",
        hovermode="x unified",
        height=500,
    )
    st.plotly_chart(fig, width="stretch")

# --- Tab 2: Remaining balance ---
with tab2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months,
        y=[mp.remaining_balance for mp in annuity.monthly_payments],
        name="Annuity",
        fill="tozeroy",
        line=dict(width=2),
    ))
    fig.add_trace(go.Scatter(
        x=months,
        y=[mp.remaining_balance for mp in serial.monthly_payments],
        name="Serial",
        fill="tozeroy",
        line=dict(width=2),
    ))
    fig.update_layout(
        title="Remaining Loan Balance",
        xaxis_title="Month",
        yaxis_title="Balance (NOK)",
        yaxis_tickformat=",",
        hovermode="x unified",
        height=500,
    )
    st.plotly_chart(fig, width="stretch")

# --- Tab 3: Interest vs principal stacked bars ---
with tab3:
    fig = make_subplots(rows=1, cols=2, subplot_titles=["Annuity", "Serial"])

    for col_idx, summary in enumerate([annuity, serial], 1):
        years = [a.year for a in summary.annual_summaries]
        principals = [a.total_principal for a in summary.annual_summaries]
        interests = [a.total_interest for a in summary.annual_summaries]

        fig.add_trace(go.Bar(
            x=years, y=principals, name="Principal",
            marker_color="#2196F3",
            showlegend=(col_idx == 1),
        ), row=1, col=col_idx)
        fig.add_trace(go.Bar(
            x=years, y=interests, name="Interest",
            marker_color="#FF7043",
            showlegend=(col_idx == 1),
        ), row=1, col=col_idx)

    fig.update_layout(
        barmode="stack",
        title="Annual Principal vs Interest Breakdown",
        yaxis_tickformat=",",
        yaxis2_tickformat=",",
        height=500,
    )
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text="NOK", col=1)
    st.plotly_chart(fig, width="stretch")

# --- Tab 4: Cumulative cost ---
with tab4:
    ann_cum_gross = list(np.cumsum([mp.total_payment for mp in annuity.monthly_payments]))
    ann_cum_net = list(np.cumsum([mp.net_payment for mp in annuity.monthly_payments]))
    ser_cum_gross = list(np.cumsum([mp.total_payment for mp in serial.monthly_payments]))
    ser_cum_net = list(np.cumsum([mp.net_payment for mp in serial.monthly_payments]))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months, y=ann_cum_gross, name="Annuity (gross)",
                             line=dict(dash="dash", width=1), opacity=0.5))
    fig.add_trace(go.Scatter(x=months, y=ann_cum_net, name="Annuity (net after tax ded.)",
                             line=dict(width=2.5)))
    fig.add_trace(go.Scatter(x=months, y=ser_cum_gross, name="Serial (gross)",
                             line=dict(dash="dash", width=1), opacity=0.5))
    fig.add_trace(go.Scatter(x=months, y=ser_cum_net, name="Serial (net after tax ded.)",
                             line=dict(width=2.5)))
    fig.update_layout(
        title="Cumulative Cost – Gross vs Net (after 22% interest deduction)",
        xaxis_title="Month",
        yaxis_title="Cumulative cost (NOK)",
        yaxis_tickformat=",",
        hovermode="x unified",
        height=500,
    )
    st.plotly_chart(fig, width="stretch")

# --- Tab 5: Annual net cost ---
with tab5:
    years = [a.year for a in annuity.annual_summaries]
    cost_key = "net_cost_after_rental" if enable_rental else "net_cost"
    ann_net = [getattr(a, cost_key) for a in annuity.annual_summaries]
    ser_net = [getattr(a, cost_key) for a in serial.annual_summaries]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=ann_net, name="Annuity", marker_color="#2196F3"))
    fig.add_trace(go.Bar(x=years, y=ser_net, name="Serial", marker_color="#FF7043"))
    fig.update_layout(
        barmode="group",
        title=f"Annual {'Net Cost After Rental' if enable_rental else 'Net Cost'} by Year",
        xaxis_title="Year",
        yaxis_title="NOK",
        yaxis_tickformat=",",
        height=500,
    )
    st.plotly_chart(fig, width="stretch")

# --- Tab 6: Rate sensitivity ---
with tab6:
    rates = np.arange(0.02, 0.08, 0.005)
    ann_costs = []
    ser_costs = []

    for r in rates:
        test_loan = LoanParameters(
            principal=principal,
            annual_interest_rate=r,
            term_years=term_years,
            extra_fees_per_month=monthly_fee,
        )
        a, s = compare_loans(test_loan, rental)
        ann_costs.append(a.total_net_cost)
        ser_costs.append(s.total_net_cost)

    rates_pct = [r * 100 for r in rates]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rates_pct, y=ann_costs,
        name="Annuity", mode="lines+markers", line=dict(width=2),
    ))
    fig.add_trace(go.Scatter(
        x=rates_pct, y=ser_costs,
        name="Serial", mode="lines+markers", line=dict(width=2),
    ))

    # Mark current rate
    fig.add_vline(
        x=interest_rate,
        line_dash="dash",
        line_color="gray",
        annotation_text="Current rate",
    )

    fig.update_layout(
        title="Total Net Cost vs Interest Rate",
        xaxis_title="Annual interest rate (%)",
        xaxis_ticksuffix="%",
        yaxis_title="Total net cost (NOK)",
        yaxis_tickformat=",",
        hovermode="x unified",
        height=500,
    )
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Annual schedule tables
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Annual Schedules")

tab_ann, tab_ser = st.tabs(["Annuity Schedule", "Serial Schedule"])

def summary_to_df(summary):
    records = []
    for a in summary.annual_summaries:
        row = {
            "Year": a.year,
            "Principal": format_nok(a.total_principal),
            "Interest": format_nok(a.total_interest),
            "Fees": format_nok(a.total_fees),
            "Total Paid": format_nok(a.total_payments),
            "Tax Deduction": format_nok(a.tax_deduction),
            "Net Cost": format_nok(a.net_cost),
            "Balance": format_nok(a.remaining_balance),
        }
        if enable_rental:
            row["Rental (net)"] = format_nok(a.rental_income_net)
            row["Net After Rental"] = format_nok(a.net_cost_after_rental)
        records.append(row)
    return pd.DataFrame(records)

with tab_ann:
    st.dataframe(summary_to_df(annuity), width="stretch", hide_index=True)

with tab_ser:
    st.dataframe(summary_to_df(serial), width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
# Norwegian tax rules reference
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("Norwegian Tax Rules Applied"):
    st.markdown(f"""
| Rule | Detail |
|------|--------|
| **Rentefradrag** | {TAX_DEDUCTION_RATE*100:.0f}% tax deduction on all interest payments |
| **Own home rental (≥50% occupied)** | Rental income is **tax-free** |
| **Separate unit / full property** | Taxed as capital income at {TAX_DEDUCTION_RATE*100:.0f}% (minus deductible maintenance) |
| **Short-term rental (<30 days)** | First NOK 10,000/year tax-free, then 85% of excess taxed at {TAX_DEDUCTION_RATE*100:.0f}% |

These rates reflect Norwegian tax law for 2024/2025. Always verify current rates with Skatteetaten.
""")
