"""
Norwegian Property Finance Dashboard
=====================================
Run with:  streamlit run app.py

Two tools:
1. Loan Calculator – Compare annuity vs serial loans
2. Short-Term Rental Investment Analysis – Seasonal pricing, tax, cashflow
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
from extra_payments_analysis import (
    HISTORICAL_RETURNS,
    RENTEFRADRAG_RATE as EPA_RENTEFRADRAG_RATE,
    STOCK_GAIN_TAX_RATE,
    CAPITAL_INCOME_TAX_RATE,
    DEFAULT_ALTERNATIVES,
    CONSERVATIVE_ALTERNATIVES,
    OPTIMISTIC_ALTERNATIVES,
    MortgageDetails as EPAMortgageDetails,
    simulate_mortgage as epa_simulate_mortgage,
    simulate_investment,
    analyze_extra_payments,
    _estimate_pct_beating_hurdle,
)
from short_term_rental import (
    PropertyDetails,
    HighLowSeasonPricing,
    MonthlyPricing,
    OperatingCosts,
    LoanDetails,
    calculate_investment,
    format_nok as str_format_nok,
    format_pct,
    SHORT_TERM_TAX_FREE_THRESHOLD,
    SHORT_TERM_TAXABLE_SHARE,
    ORDINARY_INCOME_TAX_RATE,
    INTEREST_TAX_DEDUCTION_RATE,
    VAT_ACCOMMODATION_RATE,
    VAT_REGISTRATION_THRESHOLD,
    MONTH_NAMES,
    MONTH_DAYS,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Norsk Eiendomskalkulator",
    page_icon="🏠",
    layout="wide",
)

st.title("Norwegian Property Finance Tools")

page = st.radio(
    "Select tool",
    ["Loan Calculator", "Short-Term Rental Investment", "Extra Payments vs Investing"],
    horizontal=True,
)

# =========================================================================
# PAGE 1: LOAN CALCULATOR
# =========================================================================
if page == "Loan Calculator":
    st.markdown("Compare **annuity** and **serial** loans with Norwegian tax deductions & rental income")

    # --- Sidebar ---
    st.sidebar.header("Loan Parameters")

    principal = st.sidebar.number_input(
        "Loan amount (NOK)", min_value=100_000, max_value=50_000_000,
        value=3_500_000, step=100_000, format="%d",
    )
    interest_rate = st.sidebar.slider(
        "Annual interest rate (%)", min_value=0.5, max_value=12.0, value=4.5, step=0.1,
    )
    term_years = st.sidebar.slider("Loan term (years)", min_value=1, max_value=40, value=25)
    monthly_fee = st.sidebar.number_input(
        "Monthly fee / termingebyr (NOK)", min_value=0, max_value=500, value=50, step=10,
    )

    st.sidebar.markdown("---")
    st.sidebar.header("Rental Income")
    enable_rental = st.sidebar.checkbox("Include rental income", value=False)

    rental = None
    if enable_rental:
        monthly_rent = st.sidebar.number_input(
            "Monthly rental income (NOK)", min_value=0, max_value=100_000, value=8_000, step=500,
        )
        rental_type = st.sidebar.radio("Rental type", options=[
            "Own home (>=50% occupied) - tax-free",
            "Separate unit / full property - taxed",
            "Short-term rental (<30 days) - partially taxed",
        ])
        maintenance = 0
        if rental_type == "Separate unit / full property - taxed":
            maintenance = st.sidebar.number_input(
                "Annual maintenance cost (NOK, deductible)",
                min_value=0, max_value=200_000, value=15_000, step=1_000,
            )
        rental = RentalParameters(
            monthly_rental_income=monthly_rent,
            is_short_term="Short-term" in rental_type,
            owner_occupies_half="Own home" in rental_type,
            annual_maintenance_cost=maintenance,
        )

    # --- Calculate ---
    loan = LoanParameters(
        principal=principal, annual_interest_rate=interest_rate / 100,
        term_years=term_years, extra_fees_per_month=monthly_fee,
    )
    annuity, serial = compare_loans(loan, rental)

    # --- KPIs ---
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Annuity - First Payment", format_nok(annuity.monthly_payments[0].total_payment))
        st.metric("Serial - First Payment", format_nok(serial.monthly_payments[0].total_payment))
    with col2:
        st.metric("Annuity - Total Interest", format_nok(annuity.total_interest))
        st.metric("Serial - Total Interest", format_nok(serial.total_interest))
    with col3:
        st.metric("Annuity - Tax Deduction", format_nok(annuity.total_tax_deduction))
        st.metric("Serial - Tax Deduction", format_nok(serial.total_tax_deduction))
    with col4:
        label = "Net Cost After Rental" if enable_rental else "Net Cost"
        ann_val = annuity.total_net_cost_after_rental if enable_rental else annuity.total_net_cost
        ser_val = serial.total_net_cost_after_rental if enable_rental else serial.total_net_cost
        st.metric(f"Annuity - {label}", format_nok(ann_val))
        st.metric(f"Serial - {label}", format_nok(ser_val))

    diff = ann_val - ser_val
    if diff > 0:
        st.info(f"Serial loan saves you **{format_nok(diff)}** over {term_years} years, "
                f"but starts with a higher monthly payment "
                f"({format_nok(serial.monthly_payments[0].total_payment)} vs "
                f"{format_nok(annuity.monthly_payments[0].total_payment)}).")
    elif diff < 0:
        st.info(f"Annuity loan saves you **{format_nok(abs(diff))}** over {term_years} years.")

    # --- Comparison table ---
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

    comp_df = pd.DataFrame({
        "Annuity": [format_nok(v[0]) for v in rows.values()],
        "Serial": [format_nok(v[1]) for v in rows.values()],
        "Difference": [format_nok(v[0] - v[1]) for v in rows.values()],
    }, index=rows.keys())
    st.dataframe(comp_df, width="stretch")

    # --- Charts ---
    st.markdown("---")
    st.subheader("Charts")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Monthly Payments", "Remaining Balance", "Interest vs Principal",
        "Cumulative Cost", "Annual Net Cost", "Rate Sensitivity",
    ])
    months = [mp.month for mp in annuity.monthly_payments]

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=months, y=[mp.total_payment for mp in annuity.monthly_payments],
                                 name="Annuity", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=months, y=[mp.total_payment for mp in serial.monthly_payments],
                                 name="Serial", line=dict(width=2)))
        fig.update_layout(title="Monthly Payment Over Time", xaxis_title="Month",
                          yaxis_title="Payment (NOK)", yaxis_tickformat=",",
                          hovermode="x unified", height=500)
        st.plotly_chart(fig, width="stretch")

    with tab2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=months, y=[mp.remaining_balance for mp in annuity.monthly_payments],
                                 name="Annuity", fill="tozeroy", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=months, y=[mp.remaining_balance for mp in serial.monthly_payments],
                                 name="Serial", fill="tozeroy", line=dict(width=2)))
        fig.update_layout(title="Remaining Loan Balance", xaxis_title="Month",
                          yaxis_title="Balance (NOK)", yaxis_tickformat=",",
                          hovermode="x unified", height=500)
        st.plotly_chart(fig, width="stretch")

    with tab3:
        fig = make_subplots(rows=1, cols=2, subplot_titles=["Annuity", "Serial"])
        for col_idx, summary in enumerate([annuity, serial], 1):
            years = [a.year for a in summary.annual_summaries]
            fig.add_trace(go.Bar(x=years, y=[a.total_principal for a in summary.annual_summaries],
                                 name="Principal", marker_color="#2196F3", showlegend=(col_idx == 1)),
                          row=1, col=col_idx)
            fig.add_trace(go.Bar(x=years, y=[a.total_interest for a in summary.annual_summaries],
                                 name="Interest", marker_color="#FF7043", showlegend=(col_idx == 1)),
                          row=1, col=col_idx)
        fig.update_layout(barmode="stack", title="Annual Principal vs Interest Breakdown",
                          yaxis_tickformat=",", yaxis2_tickformat=",", height=500)
        fig.update_xaxes(title_text="Year")
        fig.update_yaxes(title_text="NOK", col=1)
        st.plotly_chart(fig, width="stretch")

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
        fig.update_layout(title="Cumulative Cost - Gross vs Net (after 22% interest deduction)",
                          xaxis_title="Month", yaxis_title="Cumulative cost (NOK)",
                          yaxis_tickformat=",", hovermode="x unified", height=500)
        st.plotly_chart(fig, width="stretch")

    with tab5:
        years = [a.year for a in annuity.annual_summaries]
        cost_key = "net_cost_after_rental" if enable_rental else "net_cost"
        ann_net = [getattr(a, cost_key) for a in annuity.annual_summaries]
        ser_net = [getattr(a, cost_key) for a in serial.annual_summaries]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=years, y=ann_net, name="Annuity", marker_color="#2196F3"))
        fig.add_trace(go.Bar(x=years, y=ser_net, name="Serial", marker_color="#FF7043"))
        fig.update_layout(barmode="group",
                          title=f"Annual {'Net Cost After Rental' if enable_rental else 'Net Cost'} by Year",
                          xaxis_title="Year", yaxis_title="NOK", yaxis_tickformat=",", height=500)
        st.plotly_chart(fig, width="stretch")

    with tab6:
        rates = np.arange(0.02, 0.08, 0.005)
        ann_costs, ser_costs = [], []
        for r in rates:
            test_loan = LoanParameters(principal=principal, annual_interest_rate=r,
                                       term_years=term_years, extra_fees_per_month=monthly_fee)
            a, s = compare_loans(test_loan, rental)
            ann_costs.append(a.total_net_cost)
            ser_costs.append(s.total_net_cost)
        rates_pct = [r * 100 for r in rates]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rates_pct, y=ann_costs, name="Annuity",
                                 mode="lines+markers", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=rates_pct, y=ser_costs, name="Serial",
                                 mode="lines+markers", line=dict(width=2)))
        fig.add_vline(x=interest_rate, line_dash="dash", line_color="gray",
                      annotation_text="Current rate")
        fig.update_layout(title="Total Net Cost vs Interest Rate",
                          xaxis_title="Annual interest rate (%)", xaxis_ticksuffix="%",
                          yaxis_title="Total net cost (NOK)", yaxis_tickformat=",",
                          hovermode="x unified", height=500)
        st.plotly_chart(fig, width="stretch")

    # --- Annual schedules ---
    st.markdown("---")
    st.subheader("Annual Schedules")
    tab_ann, tab_ser = st.tabs(["Annuity Schedule", "Serial Schedule"])

    def summary_to_df(summary):
        records = []
        for a in summary.annual_summaries:
            row = {"Year": a.year, "Principal": format_nok(a.total_principal),
                   "Interest": format_nok(a.total_interest), "Fees": format_nok(a.total_fees),
                   "Total Paid": format_nok(a.total_payments),
                   "Tax Deduction": format_nok(a.tax_deduction),
                   "Net Cost": format_nok(a.net_cost), "Balance": format_nok(a.remaining_balance)}
            if enable_rental:
                row["Rental (net)"] = format_nok(a.rental_income_net)
                row["Net After Rental"] = format_nok(a.net_cost_after_rental)
            records.append(row)
        return pd.DataFrame(records)

    with tab_ann:
        st.dataframe(summary_to_df(annuity), width="stretch", hide_index=True)
    with tab_ser:
        st.dataframe(summary_to_df(serial), width="stretch", hide_index=True)

    # --- Tax rules ---
    st.markdown("---")
    with st.expander("Norwegian Tax Rules Applied"):
        st.markdown(f"""
| Rule | Detail |
|------|--------|
| **Rentefradrag** | {TAX_DEDUCTION_RATE*100:.0f}% tax deduction on all interest payments |
| **Own home rental (>=50% occupied)** | Rental income is **tax-free** |
| **Separate unit / full property** | Taxed as capital income at {TAX_DEDUCTION_RATE*100:.0f}% (minus deductible maintenance) |
| **Short-term rental (<30 days)** | First NOK 15,000/year tax-free, then 85% of excess taxed at {TAX_DEDUCTION_RATE*100:.0f}% |

These rates reflect Norwegian tax law for 2025. Always verify current rates with Skatteetaten.
""")


# =========================================================================
# PAGE 2: SHORT-TERM RENTAL INVESTMENT ANALYSIS
# =========================================================================
elif page == "Short-Term Rental Investment":
    st.markdown("Analyze short-term rental profitability with Norwegian tax rules (korttidsutleie)")

    # --- Sidebar: Property ---
    st.sidebar.header("Property Details")
    prop_name = st.sidebar.text_input("Property name", value="Kragerø Resort 633/634")
    purchase_price = st.sidebar.number_input(
        "Purchase price (NOK)", min_value=100_000, max_value=50_000_000,
        value=3_578_340, step=100_000, format="%d",
    )
    prop_sqm = st.sidebar.number_input("Size (sqm)", min_value=10, max_value=500, value=77)
    prop_bedrooms = st.sidebar.number_input("Bedrooms", min_value=1, max_value=10, value=2)
    prop_bathrooms = st.sidebar.number_input("Bathrooms", min_value=1, max_value=5, value=2)
    prop_monthly_fees = st.sidebar.number_input(
        "Monthly fees / felleskostnader (NOK)", min_value=0, max_value=30_000,
        value=1_371, step=100,
    )
    prop_property_tax = st.sidebar.number_input(
        "Annual property tax / eiendomsskatt (NOK)", min_value=0, max_value=50_000, value=7_877, step=500,
    )
    prop_insurance = st.sidebar.number_input(
        "Annual insurance (NOK)", min_value=0, max_value=50_000, value=0, step=500,
    )
    prop_maintenance = st.sidebar.number_input(
        "Annual maintenance (NOK)", min_value=0, max_value=100_000, value=10_000, step=1_000,
    )
    prop_utilities = st.sidebar.number_input(
        "Annual utilities (NOK)", min_value=0, max_value=100_000, value=0, step=1_000,
    )

    prop = PropertyDetails(
        name=prop_name, purchase_price=purchase_price, sqm=prop_sqm,
        bedrooms=prop_bedrooms, bathrooms=prop_bathrooms,
        monthly_fees=prop_monthly_fees, annual_property_tax=prop_property_tax,
        annual_insurance=prop_insurance,
        annual_maintenance=prop_maintenance, annual_utilities=prop_utilities,
    )

    # --- Sidebar: Financing ---
    st.sidebar.markdown("---")
    st.sidebar.header("Financing")
    str_use_loan = st.sidebar.checkbox("Finance with loan", value=True)
    str_loan = None
    if str_use_loan:
        str_loan_amount = st.sidebar.number_input(
            "Loan amount (NOK)", min_value=0, max_value=50_000_000,
            value=int(purchase_price * 0.75), step=100_000, format="%d",
        )
        str_interest = st.sidebar.slider(
            "Interest rate (%)", min_value=0.5, max_value=12.0, value=5.0, step=0.1,
            key="str_interest",
        )
        str_term = st.sidebar.slider(
            "Loan term (years)", min_value=1, max_value=40, value=25, key="str_term",
        )
        str_loan_type = st.sidebar.radio("Loan type", ["annuity", "serial"], key="str_loan_type")
        str_loan = LoanDetails(
            loan_amount=str_loan_amount, annual_interest_rate=str_interest / 100,
            term_years=str_term, loan_type=str_loan_type,
        )

    # --- Sidebar: Own use ---
    st.sidebar.markdown("---")
    own_use = st.sidebar.slider("Own-use nights per year", min_value=0, max_value=180, value=30)

    # --- Sidebar: Operating costs ---
    st.sidebar.markdown("---")
    st.sidebar.header("Operating Costs")
    platform_rate = st.sidebar.slider(
        "Platform commission (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.5,
    ) / 100
    cleaning_cost = st.sidebar.number_input(
        "Cleaning cost per turnover (NOK)", min_value=0, max_value=5_000, value=900, step=50,
    )
    laundry_cost = st.sidebar.number_input(
        "Laundry per turnover (NOK)", min_value=0, max_value=2_000, value=250, step=50,
    )
    consumables = st.sidebar.number_input(
        "Consumables per turnover (NOK)", min_value=0, max_value=1_000, value=150, step=25,
    )
    avg_stay = st.sidebar.slider(
        "Average stay (nights)", min_value=1.0, max_value=14.0, value=3.5, step=0.5,
    )
    cleaning_fee_guest = st.sidebar.number_input(
        "Cleaning fee charged to guest (NOK)", min_value=0, max_value=3_000, value=800, step=50,
    )
    annual_furnishing = st.sidebar.number_input(
        "Annual furnishing refresh (NOK)", min_value=0, max_value=50_000, value=12_000, step=1_000,
    )

    ops = OperatingCosts(
        platform_commission_rate=platform_rate,
        cleaning_cost_per_turnover=cleaning_cost,
        laundry_per_turnover=laundry_cost,
        consumables_per_turnover=consumables,
        annual_furnishing_refresh=annual_furnishing,
    )

    # --- Pricing model selection ---
    st.markdown("---")
    st.subheader("Seasonal Pricing")

    pricing_mode = st.radio(
        "Pricing model",
        ["High / Low / Shoulder Season", "Month-by-Month"],
        horizontal=True,
    )

    if pricing_mode == "High / Low / Shoulder Season":
        col_h, col_s, col_l = st.columns(3)
        with col_h:
            st.markdown("**High Season** (Jun-Aug)")
            hl_high_rate = st.number_input("Nightly rate (NOK)", value=2_200, step=100, key="hl_high")
            hl_high_occ = st.slider("Occupancy (%)", 0, 100, 70, key="hl_high_occ") / 100
        with col_s:
            st.markdown("**Shoulder Season** (May, Sep)")
            hl_shoulder_rate = st.number_input("Nightly rate (NOK)", value=1_400, step=100, key="hl_shoulder")
            hl_shoulder_occ = st.slider("Occupancy (%)", 0, 100, 40, key="hl_shoulder_occ") / 100
        with col_l:
            st.markdown("**Low Season** (Oct-Apr)")
            hl_low_rate = st.number_input("Nightly rate (NOK)", value=900, step=100, key="hl_low")
            hl_low_occ = st.slider("Occupancy (%)", 0, 100, 15, key="hl_low_occ") / 100

        pricing = HighLowSeasonPricing(
            high_season_nightly_rate=hl_high_rate, low_season_nightly_rate=hl_low_rate,
            shoulder_nightly_rate=hl_shoulder_rate,
            high_season_occupancy=hl_high_occ, low_season_occupancy=hl_low_occ,
            shoulder_occupancy=hl_shoulder_occ,
            cleaning_fee_per_stay=cleaning_fee_guest, avg_stay_nights=avg_stay,
        )
    else:
        st.markdown("Set nightly rate and expected occupancy for each month:")
        default_rates = [800, 1000, 900, 1000, 1300, 2000, 2500, 2200, 1400, 1000, 800, 1200]
        default_occs = [10, 20, 12, 15, 35, 60, 85, 65, 35, 15, 8, 25]

        month_data = []
        cols = st.columns(6)
        for i in range(12):
            with cols[i % 6]:
                st.markdown(f"**{MONTH_NAMES[i]}**")
                rate = st.number_input(
                    f"Rate", value=default_rates[i], step=100,
                    key=f"m_rate_{i}", label_visibility="collapsed",
                )
                occ = st.slider(
                    f"Occ%", 0, 100, default_occs[i], key=f"m_occ_{i}",
                    label_visibility="collapsed",
                )
                month_data.append({"month": MONTH_NAMES[i], "nightly_rate": rate, "occupancy": occ / 100})

        pricing = MonthlyPricing(
            months=month_data,
            cleaning_fee_per_stay=cleaning_fee_guest,
            avg_stay_nights=avg_stay,
        )

    # --- Calculate ---
    result = calculate_investment(prop, pricing, ops, str_loan, own_use)

    # --- KPI row ---
    st.markdown("---")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Gross Income", str_format_nok(result.total_gross_income))
    with c2:
        st.metric("NOI", str_format_nok(result.net_operating_income))
    with c3:
        st.metric("Post-tax Cashflow", str_format_nok(result.post_tax_cashflow))
    with c4:
        st.metric("Gross Yield", format_pct(result.gross_yield))
    with c5:
        st.metric("Net Yield", format_pct(result.net_yield))

    if result.post_tax_cashflow < 0:
        st.warning(f"Annual net cost: **{str_format_nok(abs(result.post_tax_cashflow))}** "
                   f"({str_format_nok(abs(result.post_tax_cashflow) // 12)}/month). "
                   f"Booked {result.booked_nights_total:.0f} nights at "
                   f"{format_pct(result.overall_occupancy)} occupancy.")
    else:
        st.success(f"Annual net profit: **{str_format_nok(result.post_tax_cashflow)}** "
                   f"({str_format_nok(result.post_tax_cashflow // 12)}/month). "
                   f"Booked {result.booked_nights_total:.0f} nights at "
                   f"{format_pct(result.overall_occupancy)} occupancy.")

    if result.own_use_nights > 0 and result.total_annual_cost > 0:
        st.info(f"Effective cost per own-use night: "
                f"**{str_format_nok(result.cost_per_own_night)}** "
                f"({result.own_use_nights} nights/year)")

    # --- Monthly breakdown table ---
    st.markdown("---")
    st.subheader("Monthly Breakdown")
    mb_records = []
    for m in result.monthly_breakdown:
        op_cost = m.platform_fees + m.cleaning_costs + m.laundry_costs + m.consumable_costs
        mb_records.append({
            "Month": m.month,
            "Rate": str_format_nok(m.nightly_rate),
            "Occ%": f"{m.occupancy*100:.0f}%",
            "Nights": f"{m.booked_nights:.1f}",
            "Turnovers": f"{m.num_turnovers:.1f}",
            "Gross": str_format_nok(m.gross_rental_income),
            "Op Costs": str_format_nok(op_cost),
            "Net": str_format_nok(m.net_rental_income),
        })
    st.dataframe(pd.DataFrame(mb_records), width="stretch", hide_index=True)

    # --- Charts ---
    st.markdown("---")
    st.subheader("Charts")
    str_tab1, str_tab2, str_tab3, str_tab4 = st.tabs([
        "Revenue by Month", "Occupancy & Rates", "P&L Waterfall", "Financial Summary",
    ])

    with str_tab1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[m.month for m in result.monthly_breakdown],
            y=[m.gross_rental_income for m in result.monthly_breakdown],
            name="Gross rental", marker_color="#2196F3",
        ))
        fig.add_trace(go.Bar(
            x=[m.month for m in result.monthly_breakdown],
            y=[m.net_rental_income for m in result.monthly_breakdown],
            name="Net rental (after op costs)", marker_color="#66BB6A",
        ))
        fig.update_layout(barmode="group", title="Monthly Revenue",
                          yaxis_title="NOK", yaxis_tickformat=",", height=500)
        st.plotly_chart(fig, width="stretch")

    with str_tab2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(
            x=[m.month for m in result.monthly_breakdown],
            y=[m.occupancy * 100 for m in result.monthly_breakdown],
            name="Occupancy %", marker_color="#2196F3", opacity=0.6,
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=[m.month for m in result.monthly_breakdown],
            y=[m.nightly_rate for m in result.monthly_breakdown],
            name="Nightly rate", mode="lines+markers",
            line=dict(color="#FF7043", width=2),
        ), secondary_y=True)
        fig.update_yaxes(title_text="Occupancy (%)", range=[0, 100], secondary_y=False)
        fig.update_yaxes(title_text="Nightly rate (NOK)", tickformat=",", secondary_y=True)
        fig.update_layout(title="Occupancy & Nightly Rate by Month", height=500)
        st.plotly_chart(fig, width="stretch")

    with str_tab3:
        labels = ["Gross\nIncome", "Platform\nFees", "Cleaning\n& Laundry",
                  "Other\nOp Costs", "Property\nCosts", "Loan\nPayments",
                  "Tax", "Interest\nDeduction", "Post-tax\nCashflow"]
        values = [
            result.total_gross_income, -result.platform_fees,
            -(result.cleaning_costs + result.laundry_costs + result.consumable_costs),
            -(result.furnishing_refresh + result.marketing_costs + result.property_management_fees),
            -result.total_property_costs, -result.annual_loan_payment,
            -result.rental_income_tax, result.interest_tax_deduction,
            result.post_tax_cashflow,
        ]

        running = 0
        bottoms, colors = [], []
        for i, v in enumerate(values):
            if i == len(values) - 1:
                bottoms.append(0)
                colors.append("#66BB6A" if v >= 0 else "#EF5350")
            else:
                bottoms.append(running if v >= 0 else running + v)
                colors.append("#2196F3" if v >= 0 else "#FF7043")
                running += v

        fig = go.Figure(go.Bar(
            x=labels, y=[abs(v) for v in values], base=bottoms,
            marker_color=colors, text=[str_format_nok(v) for v in values],
            textposition="inside", textfont_size=10,
        ))
        fig.update_layout(title="Annual P&L Waterfall", yaxis_title="NOK",
                          yaxis_tickformat=",", height=550, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    with str_tab4:
        # Financial summary cards
        col_rev, col_cost, col_net = st.columns(3)
        with col_rev:
            st.markdown("**Revenue**")
            st.markdown(f"- Gross rental: {str_format_nok(result.gross_rental_income)}")
            st.markdown(f"- Cleaning fees: {str_format_nok(result.cleaning_fee_income)}")
            st.markdown(f"- **Total: {str_format_nok(result.total_gross_income)}**")
        with col_cost:
            st.markdown("**Costs**")
            st.markdown(f"- Operating: {str_format_nok(result.total_operating_costs)}")
            st.markdown(f"- Property: {str_format_nok(result.total_property_costs)}")
            if result.annual_loan_payment > 0:
                st.markdown(f"- Loan payments: {str_format_nok(result.annual_loan_payment)}")
            st.markdown(f"- Rental tax: {str_format_nok(result.rental_income_tax)}")
            st.markdown(f"- Interest deduction: -{str_format_nok(result.interest_tax_deduction)}")
        with col_net:
            st.markdown("**Results**")
            st.markdown(f"- NOI: {str_format_nok(result.net_operating_income)}")
            st.markdown(f"- Post-tax cashflow: {str_format_nok(result.post_tax_cashflow)}")
            st.markdown(f"- Gross yield: {format_pct(result.gross_yield)}")
            st.markdown(f"- Net yield: {format_pct(result.net_yield)}")
            if result.annual_loan_payment > 0:
                st.markdown(f"- Cash-on-cash: {format_pct(result.cash_on_cash_return)}")
            st.markdown(f"- Booked nights: {result.booked_nights_total:.0f}")
            st.markdown(f"- Occupancy: {format_pct(result.overall_occupancy)}")

    # --- Tax rules reference ---
    st.markdown("---")
    with st.expander("Norwegian Short-Term Rental Tax Rules (2025)"):
        st.markdown(f"""
| Rule | Detail |
|------|--------|
| **Definition** | Rental periods shorter than 30 days per lease |
| **Tax-free threshold** | First NOK {SHORT_TERM_TAX_FREE_THRESHOLD:,} per property per year |
| **Taxable share** | {SHORT_TERM_TAXABLE_SHARE*100:.0f}% of income above threshold |
| **Tax rate** | {ORDINARY_INCOME_TAX_RATE*100:.0f}% ordinary income tax |
| **Rentefradrag** | {INTEREST_TAX_DEDUCTION_RATE*100:.0f}% deduction on loan interest |
| **VAT threshold** | Registration required if revenue > NOK {VAT_REGISTRATION_THRESHOLD:,}/year |
| **VAT rate** | {VAT_ACCOMMODATION_RATE*100:.0f}% on short-term accommodation |
| **Deductions** | No itemized deductions under the template model (15k + 85%) |
| **Business classification** | ~5+ units or ~500+ sqm may trigger business taxation |

Sources: [Skatteetaten](https://www.skatteetaten.no/en/person/taxes/get-the-taxes-right/property-and-belongings/houses-property-and-plots-of-land/letting-of-houses-and-property/short-term-letting-of-dwellings-and-holiday-homes/tax-rules-for-short-term-letting-of-homes-and-holiday-homes/) |
[Airbnb Tax Guide 2025](https://assets.airbnb.com/help/Airbnb_TaxGuide2025_Norway_ENGLISH.pdf) |
[BnbUtleie.no](https://bnbutleie.no/skatteregler-korttidsutleie-2025/)
""")


# =========================================================================
# PAGE 3: EXTRA PAYMENTS vs INVESTING
# =========================================================================
elif page == "Extra Payments vs Investing":
    st.markdown("Should you pay extra on your mortgage or invest the money? "
                "Analysis grounded in historical rolling-window returns.")

    # --- Sidebar: Mortgage ---
    st.sidebar.header("Your Mortgage")
    epa_balance = st.sidebar.number_input(
        "Remaining balance (NOK)", min_value=100_000, max_value=50_000_000,
        value=3_500_000, step=100_000, format="%d", key="epa_bal",
    )
    epa_rate = st.sidebar.slider(
        "Interest rate (%)", min_value=0.5, max_value=12.0, value=5.0, step=0.1, key="epa_rate",
    )
    epa_years = st.sidebar.slider(
        "Remaining term (years)", min_value=1, max_value=40, value=20, key="epa_years",
    )
    epa_loan_type = st.sidebar.radio("Loan type", ["annuity", "serial"], key="epa_type")

    st.sidebar.markdown("---")
    st.sidebar.header("Extra Payment Amounts")
    epa_extra_1 = st.sidebar.number_input("Scenario 1 (NOK/mo)", value=2_000, step=500, key="epa_e1")
    epa_extra_2 = st.sidebar.number_input("Scenario 2 (NOK/mo)", value=5_000, step=500, key="epa_e2")
    epa_extra_3 = st.sidebar.number_input("Scenario 3 (NOK/mo)", value=10_000, step=500, key="epa_e3")
    epa_extras = sorted(set(int(e) for e in [epa_extra_1, epa_extra_2, epa_extra_3] if e > 0))

    st.sidebar.markdown("---")
    st.sidebar.header("Freed Cashflow")
    st.sidebar.caption("Once you pay off the mortgage early, the freed-up payment "
                       "gets invested. What return do you assume on it?")
    epa_reinvest_choice = st.sidebar.selectbox(
        "Reinvest freed cash at",
        ["High-yield savings (3.5%, risk-free)", "Bond fund (4.8%)",
         "Global index (8.1%)", "US equity (10.0%)"],
        index=0, key="epa_reinvest",
    )
    _reinvest_map = {
        "High-yield savings (3.5%, risk-free)": (0.035, CAPITAL_INCOME_TAX_RATE),
        "Bond fund (4.8%)": (0.048, CAPITAL_INCOME_TAX_RATE),
        "Global index (8.1%)": (0.0808, STOCK_GAIN_TAX_RATE),
        "US equity (10.0%)": (0.10, STOCK_GAIN_TAX_RATE),
    }
    epa_reinvest_return, epa_reinvest_tax = _reinvest_map[epa_reinvest_choice]

    mortgage = EPAMortgageDetails(
        remaining_balance=epa_balance,
        annual_interest_rate=epa_rate / 100,
        remaining_years=epa_years,
        loan_type=epa_loan_type,
    )

    effective_rate = mortgage.annual_interest_rate * (1 - EPA_RENTEFRADRAG_RATE)

    # --- KPI row ---
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Nominal Rate", f"{mortgage.annual_interest_rate*100:.2f}%")
    with k2:
        st.metric("After Rentefradrag", f"{effective_rate*100:.2f}%")
    with k3:
        needed_ask = effective_rate / (1 - STOCK_GAIN_TAX_RATE)
        st.metric("Need pre-tax (ASK)", f"{needed_ask*100:.2f}%")
    with k4:
        needed_savings = effective_rate / (1 - CAPITAL_INCOME_TAX_RATE)
        st.metric("Need pre-tax (savings)", f"{needed_savings*100:.2f}%")

    st.info(f"Your effective mortgage cost after rentefradrag is **{effective_rate*100:.2f}%**. "
            f"Any alternative must beat this after tax to justify investing instead of paying down the mortgage.")

    # =================================================================
    # Section 1: Historical Reference Data
    # =================================================================
    st.markdown("---")
    st.subheader("Historical Rolling-Window Returns")
    st.caption("All figures are annualized nominal total returns. "
               "Rolling windows show the range of outcomes an investor actually experienced.")

    hist_tab1, hist_tab2, hist_tab3 = st.tabs([
        "Reference Table", "Rolling Window Chart", "Beat-the-Mortgage Odds",
    ])

    with hist_tab1:
        ref_rows = []
        for key, label in [
            ("sp500", "S&P 500"),
            ("msci_world", "MSCI World"),
            ("global_bonds", "Global Bonds"),
        ]:
            d = HISTORICAL_RETURNS[key]
            r10 = d["rolling_10yr"]
            r20 = d.get("rolling_20yr", {})
            ref_rows.append({
                "Index": label,
                "Source Period": d["source"],
                "10yr Worst": f"{r10['worst']*100:+.1f}%",
                "10yr 25th": f"{r10['p25']*100:.1f}%",
                "10yr Median": f"{r10['median']*100:.1f}%",
                "10yr 75th": f"{r10['p75']*100:.1f}%",
                "10yr Best": f"{r10['best']*100:.1f}%",
                "20yr Worst": f"{r20.get('worst', 0)*100:+.1f}%" if r20 else "—",
                "20yr Median": f"{r20.get('median', 0)*100:.1f}%" if r20 else "—",
                "20yr Best": f"{r20.get('best', 0)*100:.1f}%" if r20 else "—",
            })
        st.dataframe(pd.DataFrame(ref_rows), width="stretch", hide_index=True)

        infl = HISTORICAL_RETURNS["norwegian_inflation"]
        st.markdown(f"**Norwegian CPI inflation:** 25yr avg {infl['avg_25yr']*100:.1f}%, "
                    f"recent decade {infl['recent_decade_avg']*100:.1f}% "
                    f"(2022–23 spike pulls recent average up)")

        with st.expander("Data Sources"):
            st.markdown("""
| Source | Coverage |
|--------|----------|
| **S&P 500** | QuantFlowLab (1928–2025), Trade That Swing, Crestmont Research |
| **MSCI World** | MSCI factsheet, Curvo.eu, InvestingInTheWeb; median from Cautaerts analysis (1970–2018) |
| **Global Bonds** | Alliance Bernstein (Bloomberg Global Agg, 30yr hedged USD), YCharts |
| **Oslo Bors** | World Bank / TheGlobalEconomy (1997–2021), arithmetic mean 12.0% |
| **Norwegian CPI** | SSB, World Bank, Macrotrends |
""")

    with hist_tab2:
        fig = go.Figure()
        for key, label, color in [
            ("sp500", "S&P 500", "#2196F3"),
            ("msci_world", "MSCI World", "#66BB6A"),
            ("global_bonds", "Global Bonds", "#FF7043"),
        ]:
            r10 = HISTORICAL_RETURNS[key]["rolling_10yr"]
            percentiles = ["Worst", "25th", "Median", "75th", "Best"]
            values = [r10["worst"]*100, r10["p25"]*100, r10["median"]*100, r10["p75"]*100, r10["best"]*100]
            fig.add_trace(go.Scatter(
                x=percentiles, y=values, mode="lines+markers", name=label,
                line=dict(color=color, width=2.5), marker=dict(size=10),
            ))

        fig.add_hline(
            y=effective_rate*100, line_dash="dash", line_color="red", line_width=2,
            annotation_text=f"Your hurdle: {effective_rate*100:.2f}% (after tax)",
            annotation_position="top left",
        )
        hurdle_ask = effective_rate / (1 - STOCK_GAIN_TAX_RATE) * 100
        fig.add_hline(
            y=hurdle_ask, line_dash="dot", line_color="darkred", line_width=1.5,
            annotation_text=f"Pre-tax hurdle (ASK): {hurdle_ask:.2f}%",
            annotation_position="bottom right",
        )

        fig.update_layout(
            title="Rolling 10-Year Return Distribution by Index",
            xaxis_title="Percentile", yaxis_title="Annualized Return (%)",
            yaxis_ticksuffix="%", height=500, hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    with hist_tab3:
        st.markdown("What percentage of historical rolling 10-year windows would have "
                    "beaten your mortgage's effective cost?")

        odds_rows = []
        for key, label, tax in [
            ("msci_world", "Global Index Fund (ASK)", STOCK_GAIN_TAX_RATE),
            ("sp500", "US Equity (ASK)", STOCK_GAIN_TAX_RATE),
            ("global_bonds", "Bond Fund", CAPITAL_INCOME_TAX_RATE),
        ]:
            r10 = HISTORICAL_RETURNS[key]["rolling_10yr"]
            needed = effective_rate / (1 - tax)
            pct = _estimate_pct_beating_hurdle(r10, needed)
            after_tax_median = r10["median"] * (1 - tax)
            verdict = "INVEST" if after_tax_median > effective_rate else "PAY LOAN"
            odds_rows.append({
                "Asset Class": label,
                "Tax Rate": f"{tax*100:.1f}%",
                "Need Pre-tax": f"{needed*100:.2f}%",
                "Median Return": f"{r10['median']*100:.1f}%",
                "After-tax Median": f"{after_tax_median*100:.2f}%",
                "Windows Beating Mortgage": f"{pct:.0f}%",
                "Verdict (at median)": verdict,
            })
        st.dataframe(pd.DataFrame(odds_rows), width="stretch", hide_index=True)

        # Bar chart of odds
        fig = go.Figure()
        names = [r["Asset Class"] for r in odds_rows]
        pcts = [float(r["Windows Beating Mortgage"].rstrip("%")) for r in odds_rows]
        colors = ["#66BB6A" if p >= 50 else "#EF5350" for p in pcts]
        fig.add_trace(go.Bar(x=names, y=pcts, marker_color=colors, text=[f"{p:.0f}%" for p in pcts],
                             textposition="outside"))
        fig.add_hline(y=50, line_dash="dash", line_color="gray",
                      annotation_text="50% threshold")
        fig.update_layout(title="% of Historical 10yr Windows That Beat Your Mortgage",
                          yaxis_title="Percentage (%)", yaxis_range=[0, 105], height=400)
        st.plotly_chart(fig, use_container_width=True)

        r20_available = {k: v for k, v in HISTORICAL_RETURNS.items()
                         if "rolling_20yr" in v}
        if r20_available:
            st.markdown("**20-Year Perspective:**")
            for key, data in r20_available.items():
                r20 = data["rolling_20yr"]
                st.markdown(f"- **{data['description']}**: worst 20yr window returned "
                            f"**{r20['worst']*100:+.1f}%**/yr, median **{r20['median']*100:.1f}%**/yr")
            st.markdown("No 20-year rolling window for S&P 500 has ever been negative.")

    # =================================================================
    # Section 2: Extra Payments Analysis
    # =================================================================
    if epa_extras:
        st.markdown("---")
        st.subheader("Extra Payment Scenarios")

        results = analyze_extra_payments(
            mortgage, epa_extras, alternatives=DEFAULT_ALTERNATIVES,
            reinvest_return=epa_reinvest_return, reinvest_tax=epa_reinvest_tax,
        )

        # Baseline info
        baseline_interest = results["baseline_total_interest"]
        baseline_months = results["baseline_months"]
        st.markdown(f"**Baseline:** {baseline_months} months ({baseline_months/12:.1f} years), "
                    f"total interest {format_nok(baseline_interest)}, "
                    f"after rentefradrag {format_nok(baseline_interest * (1 - EPA_RENTEFRADRAG_RATE))}")

        # Break-even table
        st.markdown("#### Break-Even Returns")
        be_rows = []
        for name, info in results["breakeven_returns"].items():
            after_tax_return = info["alt_return"] * (1 - info["alt_tax_rate"])
            be_rows.append({
                "Alternative": name,
                "Tax Rate": f"{info['alt_tax_rate']*100:.1f}%",
                "Need Pre-tax": f"{info['pretax_needed']*100:.2f}%",
                "Actual Return": f"{info['alt_return']*100:.1f}%",
                "After-tax Return": f"{after_tax_return*100:.2f}%",
                "Verdict": "INVEST" if info["beats_mortgage"] else "PAY LOAN",
            })
        st.dataframe(pd.DataFrame(be_rows), width="stretch", hide_index=True)

        # Per-scenario tabs
        scenario_tabs = st.tabs([f"+{format_nok(e)}/mo" for e in epa_extras])
        milestones = sorted(set(y for y in [5, 10, 15, 20, epa_years] if y <= epa_years))

        for tab, sc in zip(scenario_tabs, results["scenarios"]):
            with tab:
                extra = sc["extra_monthly"]
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("Months to Payoff", f"{sc['months_to_payoff']}",
                              delta=f"-{sc['months_saved']} months")
                with col_b:
                    st.metric("Interest Saved", format_nok(sc["interest_saved"]))
                with col_c:
                    st.metric("After Rentefradrag", format_nok(sc["interest_saved_after_tax"]))
                with col_d:
                    roi = (sc["interest_saved_after_tax"] / sc["total_extra_paid"] * 100
                           if sc["total_extra_paid"] > 0 else 0)
                    st.metric("Return on Extra", f"{roi:.1f}%")

                # Wealth comparison chart
                fig = go.Figure()
                mort_wealth = sc["mortgage_paydown_wealth"][:epa_years]
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(mort_wealth)+1)), y=mort_wealth,
                    name=f"Mortgage paydown", line=dict(color="#2196F3", width=3),
                ))
                alt_colors = ["#66BB6A", "#FF7043", "#AB47BC", "#EF5350"]
                reinvest_pct = results["reinvest_return"] * 100
                for i, (alt_name, alt_data) in enumerate(sc["alternatives"].items()):
                    alt_w = alt_data["wealth_by_year"][:epa_years]
                    fig.add_trace(go.Scatter(
                        x=list(range(1, len(alt_w)+1)), y=alt_w,
                        name=f"{alt_name} ({alt_data['alt_return']*100:.1f}%)",
                        line=dict(color=alt_colors[i % len(alt_colors)], width=1.5),
                    ))
                fig.update_layout(
                    title=f"Net Wealth: +{format_nok(extra)}/mo Mortgage Paydown vs Alternatives "
                          f"(equal budget; freed cash reinvested at {reinvest_pct:.1f}%)",
                    xaxis_title="Years", yaxis_title="Net Wealth Gain (NOK)",
                    yaxis_tickformat=",", hovermode="x unified", height=500,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Milestone table
                m_rows = []
                for y in milestones:
                    if y > len(sc["mortgage_paydown_wealth"]):
                        continue
                    row = {"Year": y, "Mortgage Paydown": format_nok(sc["mortgage_paydown_wealth"][y-1])}
                    best_name, best_val = "Mortgage", sc["mortgage_paydown_wealth"][y-1]
                    for alt_name, alt_data in sc["alternatives"].items():
                        wba = alt_data["wealth_by_year"]
                        val = wba[y-1] if y <= len(wba) else alt_data["net_at_end"]
                        row[alt_name[:25]] = format_nok(val)
                        if val > best_val:
                            best_name, best_val = alt_name, val
                    row["Best"] = best_name[:20]
                    m_rows.append(row)
                st.dataframe(pd.DataFrame(m_rows), width="stretch", hide_index=True)

        # =================================================================
        # Section 2b: Three leverage strategies (incl. interest-only)
        # =================================================================
        st.markdown("---")
        st.subheader("Three Leverage Strategies (incl. Interest-Only)")
        st.caption("Same monthly budget, three ways to deploy it. Interest-only "
                   "(avdragsfrihet) never reduces principal — you keep the full loan "
                   "outstanding and invest the principal portion, maximising both the "
                   "tax deduction and your market exposure. All strategies reinvest the "
                   "22% rentefradrag refund.")

        lev_c1, lev_c2 = st.columns(2)
        with lev_c1:
            lev_extra = st.selectbox(
                "Extra payment / month",
                options=epa_extras,
                index=len(epa_extras) - 1,
                format_func=lambda x: f"{x:,} kr/mo",
                key="lev_extra",
            )
        with lev_c2:
            lev_fund_name = st.selectbox(
                "Invest the freed money in",
                options=[a.name for a in DEFAULT_ALTERNATIVES],
                index=0, key="lev_fund",
            )

        lev_results = analyze_extra_payments(
            mortgage, [lev_extra], alternatives=DEFAULT_ALTERNATIVES,
            reinvest_return=epa_reinvest_return, reinvest_tax=epa_reinvest_tax,
        )
        lsc = lev_results["scenarios"][0]
        lev_fund = next(a for a in DEFAULT_ALTERNATIVES if a.name == lev_fund_name)

        prepay_series = lsc["mortgage_paydown_wealth"]
        amort_series = lsc["alternatives"][lev_fund_name]["wealth_by_year"]
        io_series = lsc["interest_only"][lev_fund_name]["wealth_by_year"]
        yrs = list(range(1, len(prepay_series) + 1))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=yrs, y=prepay_series, name="Prepay (max paydown)",
                                 line=dict(color="#2196F3", width=2.5)))
        fig.add_trace(go.Scatter(x=yrs, y=amort_series,
                                 name=f"Amortize + invest extra ({lev_fund.annual_return*100:.1f}%)",
                                 line=dict(color="#66BB6A", width=2.5)))
        fig.add_trace(go.Scatter(x=yrs, y=io_series,
                                 name=f"Interest-only / max leverage ({lev_fund.annual_return*100:.1f}%)",
                                 line=dict(color="#FF7043", width=2.5)))
        fig.update_layout(
            title=f"Net Worth: Prepay vs Amortize vs Interest-Only — +{format_nok(lev_extra)}/mo into {lev_fund_name}",
            xaxis_title="Years", yaxis_title="Net Worth Gain (NOK)",
            yaxis_tickformat=",", hovermode="x unified", height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        lev_rows = []
        for y in milestones:
            if y > len(prepay_series):
                continue
            vals = {"Prepay (max paydown)": prepay_series[y-1],
                    "Amortize + invest": amort_series[y-1],
                    "Interest-only (max leverage)": io_series[y-1]}
            best = max(vals, key=vals.get)
            lev_rows.append({
                "Year": y,
                "Prepay": format_nok(vals["Prepay (max paydown)"]),
                "Amortize + invest": format_nok(vals["Amortize + invest"]),
                "Interest-only": format_nok(vals["Interest-only (max leverage)"]),
                "Best": best,
            })
        st.dataframe(pd.DataFrame(lev_rows), width="stretch", hide_index=True)

        io_end = io_series[-1]
        pp_end = prepay_series[-1]
        fund_after_tax = lev_fund.annual_return * (1 - lev_fund.tax_rate)
        if fund_after_tax > effective_rate:
            st.success(f"At {lev_fund.annual_return*100:.1f}% ({fund_after_tax*100:.2f}% after tax), "
                       f"interest-only ends **{format_nok(io_end)}** vs prepay **{format_nok(pp_end)}** — "
                       f"leverage pays off because the fund beats your {effective_rate*100:.2f}% effective mortgage cost.")
        else:
            st.warning(f"At {lev_fund.annual_return*100:.1f}% ({fund_after_tax*100:.2f}% after tax), "
                       f"interest-only ends **{format_nok(io_end)}** vs prepay **{format_nok(pp_end)}** — "
                       f"leverage backfires because the fund does NOT beat your {effective_rate*100:.2f}% effective cost.")

        st.error(
            "⚠️ **Interest-only is maximum leverage — know the risks:**\n"
            "- You still owe the **full original balance** at the end; it must be refinanced or repaid from the portfolio.\n"
            "- A market crash near the end is devastating: the debt is fixed, the portfolio is not.\n"
            "- Norwegian rules (*boliglånsforskrift*) generally only allow avdragsfrihet when **LTV < 60%**.\n"
            "- Returns shown are smooth averages; real markets are volatile and sequence-of-returns matters.\n"
            "- This is not advice — it's the arithmetic of leverage under your assumptions."
        )

        # =================================================================
        # Section 3: Balance trajectory
        # =================================================================
        st.markdown("---")
        st.subheader("Mortgage Balance Trajectories")
        fig = go.Figure()
        colors_traj = ["#78909C", "#2196F3", "#66BB6A", "#FF7043", "#AB47BC"]
        for i, extra in enumerate([0] + epa_extras):
            sched = epa_simulate_mortgage(mortgage, extra)
            months_list = [s["month"]/12 for s in sched]
            balances = [s["balance"] for s in sched]
            label = "No extra" if extra == 0 else f"+{format_nok(extra)}/mo"
            fig.add_trace(go.Scatter(
                x=months_list, y=balances, name=label,
                line=dict(color=colors_traj[i % len(colors_traj)], width=2),
            ))
        fig.update_layout(
            title="Mortgage Balance Over Time",
            xaxis_title="Years", yaxis_title="Remaining Balance (NOK)",
            yaxis_tickformat=",", hovermode="x unified", height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

        # =================================================================
        # Section 4: Sensitivity heatmap
        # =================================================================
        st.markdown("---")
        st.subheader("Sensitivity: Interest Saved (after tax)")

        rates_sens = [0.03, 0.04, 0.05, 0.055, 0.06, 0.07]
        extras_sens = [1000, 2000, 3000, 5000, 7500, 10000]

        heat_data = []
        for extra in extras_sens:
            row = []
            for rate in rates_sens:
                temp_m = EPAMortgageDetails(epa_balance, rate, epa_years, epa_loan_type)
                base = epa_simulate_mortgage(temp_m, 0)
                with_extra = epa_simulate_mortgage(temp_m, extra)
                saved = sum(b["interest"] for b in base) - sum(e["interest"] for e in with_extra)
                row.append(saved * (1 - EPA_RENTEFRADRAG_RATE))
            heat_data.append(row)

        heat_array = np.array(heat_data)
        fig = go.Figure(data=go.Heatmap(
            z=heat_array / 1000,
            x=[f"{r*100:.1f}%" for r in rates_sens],
            y=[f"{e:,.0f} kr" for e in extras_sens],
            colorscale="YlOrRd",
            text=[[f"{v/1000:.0f}k" for v in row] for row in heat_data],
            texttemplate="%{text}",
            colorbar_title="Saved (k NOK)",
        ))
        fig.update_layout(
            title="Interest Saved (thousands NOK, after 22% rentefradrag) by Rate & Extra Payment",
            xaxis_title="Interest Rate", yaxis_title="Extra Payment / Month",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    # =================================================================
    # Section 5: Conservative vs Optimistic scenarios
    # =================================================================
    st.markdown("---")
    st.subheader("Scenario Range: Conservative vs Median vs Optimistic")
    st.caption("Based on 25th, 50th, and 75th percentile of historical rolling 10-year windows. "
               "Mortgage paydown is identical across columns — it doesn't depend on how markets perform. "
               "✓ = beats mortgage paydown, ✗ = mortgage wins.")

    scenario_extra = st.selectbox(
        "Extra payment amount for scenario comparison",
        options=[2000, 5000, 10000],
        index=1,
        format_func=lambda x: f"{x:,} kr/mo",
    )

    scenario_sets = [
        ("Conservative (25th pctl)", CONSERVATIVE_ALTERNATIVES),
        ("Median (50th pctl)", DEFAULT_ALTERNATIVES),
        ("Optimistic (75th pctl)", OPTIMISTIC_ALTERNATIVES),
    ]

    scenario_cols = st.columns(3)
    for col, (label, alts) in zip(scenario_cols, scenario_sets):
        with col:
            st.markdown(f"**{label}**")
            res = analyze_extra_payments(
                mortgage, [scenario_extra], alternatives=alts,
                reinvest_return=epa_reinvest_return, reinvest_tax=epa_reinvest_tax,
            )
            sc = res["scenarios"][0]
            mort_w = sc["mortgage_paydown_wealth"][-1]
            st.markdown(f"Mortgage paydown: **{format_nok(mort_w)}**")
            for alt_name, alt_data in sc["alternatives"].items():
                val = alt_data["net_at_end"]
                icon = "✓" if val > mort_w else "✗"
                short = alt_name.split("(")[0].strip()[:22]
                st.markdown(f"- {icon} {short} ({alt_data['alt_return']*100:.1f}%): "
                            f"**{format_nok(val)}**")

    # Summary
    st.markdown("---")
    with st.expander("Summary & Decision Framework"):
        st.markdown(f"""
**Your effective mortgage cost after rentefradrag: {effective_rate*100:.2f}%**

**Rule of thumb:**
- If you can earn **> {effective_rate*100:.1f}%** after tax elsewhere: invest
- If not: pay down the mortgage

**Historical verdict at {mortgage.annual_interest_rate*100:.1f}% mortgage rate:**

| Factor | Detail |
|--------|--------|
| **MSCI World median** | {HISTORICAL_RETURNS['msci_world']['rolling_10yr']['median']*100:.1f}% pre-tax, ~{HISTORICAL_RETURNS['msci_world']['rolling_10yr']['median']*(1-STOCK_GAIN_TAX_RATE)*100:.2f}% after ASK tax |
| **S&P 500 median** | {HISTORICAL_RETURNS['sp500']['rolling_10yr']['median']*100:.1f}% pre-tax, ~{HISTORICAL_RETURNS['sp500']['rolling_10yr']['median']*(1-STOCK_GAIN_TAX_RATE)*100:.2f}% after ASK tax |
| **Global bonds** | {HISTORICAL_RETURNS['global_bonds']['long_term_avg']*100:.1f}% pre-tax, ~{HISTORICAL_RETURNS['global_bonds']['long_term_avg']*(1-CAPITAL_INCOME_TAX_RATE)*100:.2f}% after tax |
| **20yr S&P 500 worst** | {HISTORICAL_RETURNS['sp500']['rolling_20yr']['worst']*100:.1f}%/yr — no negative 20yr window ever |

**Factors beyond pure return:**
- Mortgage paydown is **risk-free** (guaranteed {effective_rate*100:.2f}% return)
- Stocks average higher but can drop 30–50% in any given year
- **Liquidity:** extra mortgage payments are locked in; investments are accessible
- **Behavioral:** forced paydown builds discipline; investments can be raided
- **Flexibility:** lower mortgage = lower required income

**Data sources:** S&P 500 (QuantFlowLab, Crestmont Research 1926–2024), MSCI World (MSCI factsheet, Curvo.eu 1970–2024),
Global Bonds (Bloomberg Global Agg, Alliance Bernstein), Norwegian CPI (SSB, World Bank).
""")
