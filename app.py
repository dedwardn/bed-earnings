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
    ["Loan Calculator", "Short-Term Rental Investment"],
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
