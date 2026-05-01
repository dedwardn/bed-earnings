"""
Example: Kragerø Resort Apartment Investment Analysis
=====================================================

Based on Finn listing 461543499 – Stabbestadveien 1, Kragerø Resort 207/307
(Krogsveen listing). 2 bedrooms, 2 bathrooms, 3 terraces, sea view,
boat berth, golf rights. Sold fully furnished.

Uses REAL collected pricing data from kragero_pricing_data.py, sourced from:
- KAYAK, Momondo, HotelsCombined, Travelocity hotel room rates
- Airbnb comparable apartment/cabin listings in Kragerø area
- Booking.com Kragerø Resort rates
- Resort's own booking system (booking.krageroresort.no)
- Krogsveen listing reported rental income: 116,676 NOK (2024)

Two management scenarios:
1. Independent (self-managed via Airbnb/Booking.com)
2. Resort pool (Fredensborg Fritid, estimated 30% commission)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os

from short_term_rental import (
    PropertyDetails,
    HighLowSeasonPricing,
    MonthlyPricing,
    OperatingCosts,
    LoanDetails,
    calculate_investment,
    compare_scenarios,
    print_investment_summary,
    print_scenario_comparison,
    format_nok,
    MONTH_NAMES,
)

from kragero_pricing_data import (
    ESTIMATED_MONTHLY_PRICING_2BR_APARTMENT,
    RENTAL_MANAGEMENT,
    PROPERTY_COSTS_207_307,
)

os.makedirs("output", exist_ok=True)

# ---------------------------------------------------------------------------
# Property: Kragerø Resort 207/307
# ---------------------------------------------------------------------------
kragero = PropertyDetails(
    name="Kragerø Resort 207/307 – Stabbestadveien 1",
    purchase_price=3_900_000,
    sqm=70,
    bedrooms=2,
    bathrooms=2,
    monthly_fees=PROPERTY_COSTS_207_307["felleskostnader_monthly_nok"],  # 1,370 kr/mo
    annual_property_tax=PROPERTY_COSTS_207_307["annual_property_tax_and_municipal_fees_nok"],
    annual_insurance=8_000,
    annual_maintenance=15_000,
    annual_utilities=18_000,
    formuesverdi=800_000,
)

# ---------------------------------------------------------------------------
# Pricing Model 1: High/Low Season (simplified from collected data)
# ---------------------------------------------------------------------------
# Derived from the monthly data: summer avg ~2,467 NOK, shoulder ~1,600, low ~1,200
high_low_pricing = HighLowSeasonPricing(
    high_season_nightly_rate=2_467,    # Jun-Aug avg from collected data
    low_season_nightly_rate=1_200,     # Oct-Apr avg from collected data
    shoulder_nightly_rate=1_600,       # May, Sep from collected data
    high_season_months=3,
    shoulder_season_months=2,
    high_season_occupancy=0.65,        # Jun-Aug avg from collected data
    low_season_occupancy=0.14,         # Oct-Apr avg from collected data
    shoulder_occupancy=0.275,          # May, Sep avg from collected data
    cleaning_fee_per_stay=800,
    avg_stay_nights=3.5,
)

# ---------------------------------------------------------------------------
# Pricing Model 2: Month-by-month variable pricing (from real collected data)
# ---------------------------------------------------------------------------
monthly_pricing_independent = MonthlyPricing(
    months=[
        {
            "month": m["month"],
            "nightly_rate": m["nightly_rate_nok"],
            "occupancy": m["occupancy_pct"] / 100,
        }
        for m in ESTIMATED_MONTHLY_PRICING_2BR_APARTMENT
    ],
    cleaning_fee_per_stay=800,
    avg_stay_nights=3.5,
)

# ---------------------------------------------------------------------------
# Pricing Model 3: Resort pool – lower occupancy matching reported income
# ---------------------------------------------------------------------------
# The reported 116,676 NOK (2024) is likely the owner's 70% share after
# resort commission. Gross bookings ≈ 166,680 NOK.
# We model this as the resort's actual achieved occupancy (lower than
# independent management) at similar rates.
resort_commission_rate = RENTAL_MANAGEMENT["commission_estimate"]["resort_pool_pct"] / 100

# Scale occupancy down so that owner's net income ≈ 116,676 NOK
# Gross from our model: 216,040. After 30% commission: 151,228.
# Reported: 116,676. Ratio: 116,676 / (216,040 * 0.70) = 0.771
# So resort achieves ~77% of our independent occupancy estimates.
RESORT_OCCUPANCY_FACTOR = 0.77

monthly_pricing_resort = MonthlyPricing(
    months=[
        {
            "month": m["month"],
            "nightly_rate": m["nightly_rate_nok"],
            "occupancy": (m["occupancy_pct"] / 100) * RESORT_OCCUPANCY_FACTOR,
        }
        for m in ESTIMATED_MONTHLY_PRICING_2BR_APARTMENT
    ],
    cleaning_fee_per_stay=0,  # Resort handles cleaning (included in commission)
    avg_stay_nights=3.5,
)

# ---------------------------------------------------------------------------
# Operating costs – Independent management
# ---------------------------------------------------------------------------
ops_independent = OperatingCosts(
    platform_commission_rate=0.03,     # Airbnb host fee
    cleaning_cost_per_turnover=900,    # Professional cleaning
    laundry_per_turnover=250,          # Linens
    consumables_per_turnover=150,      # Toiletries, coffee, etc.
    annual_furnishing_refresh=12_000,
    annual_marketing=0,
    property_management_rate=0.0,      # Self-managed
)

# Operating costs – Resort pool management
ops_resort = OperatingCosts(
    platform_commission_rate=resort_commission_rate,  # 30% to resort
    cleaning_cost_per_turnover=0,      # Included in resort commission
    laundry_per_turnover=0,            # Included in resort commission
    consumables_per_turnover=0,        # Included in resort commission
    annual_furnishing_refresh=12_000,  # Owner still pays for wear/tear
    annual_marketing=0,                # Resort handles marketing
    property_management_rate=0.0,      # Commission covers this
)

# ---------------------------------------------------------------------------
# Financing
# ---------------------------------------------------------------------------
loan = LoanDetails(
    loan_amount=2_925_000,             # 75% LTV
    annual_interest_rate=0.05,         # 5%
    term_years=25,
    loan_type="annuity",
)


# ---------------------------------------------------------------------------
# Run analysis
# ---------------------------------------------------------------------------
print("=" * 80)
print("  KRAGERØ RESORT INVESTMENT ANALYSIS")
print("  Using real collected pricing data from booking platforms")
print("=" * 80)

# Scenario A: Independent Airbnb management, 30 nights own use
print("\n\n>>> SCENARIO A: Independent Management (Airbnb/Booking), 30 nights own use")
summary_indep = calculate_investment(
    kragero, monthly_pricing_independent, ops_independent, loan, own_use_nights=30
)
print_investment_summary(summary_indep, kragero)

# Scenario B: Resort pool management, 30 nights own use
print("\n\n>>> SCENARIO B: Resort Pool (Fredensborg Fritid, ~30% commission), 30 nights own use")
summary_resort = calculate_investment(
    kragero, monthly_pricing_resort, ops_resort, loan, own_use_nights=30
)
print_investment_summary(summary_resort, kragero)

# Scenario C: High/Low model for quick estimation
print("\n\n>>> SCENARIO C: High/Low Season Estimate, 30 nights own use")
summary_hl = calculate_investment(
    kragero, high_low_pricing, ops_independent, loan, own_use_nights=30
)
print_investment_summary(summary_hl, kragero)

# ---------------------------------------------------------------------------
# Compare all scenarios
# ---------------------------------------------------------------------------
scenarios = {
    "Indep 30 own": (monthly_pricing_independent, 30),
    "Resort 30 own": (monthly_pricing_resort, 30),
    "Indep 0 own": (monthly_pricing_independent, 0),
    "Resort 0 own": (monthly_pricing_resort, 0),
    "Indep 60 own": (monthly_pricing_independent, 60),
}

# Build results manually to use different ops for resort vs independent
results = {}
for name, (pricing, own_use) in scenarios.items():
    ops = ops_resort if "Resort" in name else ops_independent
    results[name] = calculate_investment(kragero, pricing, ops, loan, own_use)

print_scenario_comparison(results)


# ---------------------------------------------------------------------------
# Data source summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("  DATA SOURCES")
print("=" * 80)
print(f"  Reported 2024 rental income (Krogsveen listing): {format_nok(116_676)}")
print(f"  Resort pool operator: {RENTAL_MANAGEMENT['operator']}")
print(f"  Estimated resort commission: {RENTAL_MANAGEMENT['commission_estimate']['resort_pool_pct']}%")
print(f"  Felleskostnader: {format_nok(PROPERTY_COSTS_207_307['felleskostnader_annual_nok'])}/year")
print(f"  Property tax & municipal fees: {format_nok(PROPERTY_COSTS_207_307['annual_property_tax_and_municipal_fees_nok'])}/year")
print(f"  Pricing data from: KAYAK, Momondo, Airbnb, Booking.com, HotelsCombined")
print()


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
BLUE = "#2196F3"
ORANGE = "#FF7043"
GREEN = "#66BB6A"
RED = "#EF5350"
PURPLE = "#AB47BC"
plt.style.use("seaborn-v0_8-whitegrid")

def nok_fmt(x, _):
    if abs(x) >= 1_000_000:
        return f"{x/1e6:.1f}M"
    if abs(x) >= 1_000:
        return f"{x/1e3:.0f}k"
    return f"{x:.0f}"

# Chart 1: Monthly revenue – Independent vs Resort Pool
fig, ax = plt.subplots(figsize=(13, 5))
months = [m.month for m in summary_indep.monthly_breakdown]
gross_indep = [m.gross_rental_income for m in summary_indep.monthly_breakdown]
net_indep = [m.net_rental_income for m in summary_indep.monthly_breakdown]
net_resort = [m.net_rental_income for m in summary_resort.monthly_breakdown]
x = np.arange(len(months))
width = 0.27
ax.bar(x - width, gross_indep, width, label="Gross (independent)", color=BLUE, alpha=0.7)
ax.bar(x, net_indep, width, label="Net (independent)", color=GREEN)
ax.bar(x + width, net_resort, width, label="Net (resort pool)", color=ORANGE)
ax.set_xticks(x)
ax.set_xticklabels(months)
ax.set_title("Kragerø Resort – Monthly Revenue: Independent vs Resort Pool", fontsize=14)
ax.set_ylabel("NOK")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
ax.legend()
plt.tight_layout()
plt.savefig("output/kragero_monthly_revenue.png", dpi=150)
plt.close()
print("Saved: output/kragero_monthly_revenue.png")

# Chart 2: Occupancy and nightly rate by month
fig, ax1 = plt.subplots(figsize=(13, 5))
occ_indep = [m.occupancy * 100 for m in summary_indep.monthly_breakdown]
occ_resort = [m.occupancy * 100 for m in summary_resort.monthly_breakdown]
rates = [m.nightly_rate for m in summary_indep.monthly_breakdown]
ax1.bar(x - 0.15, occ_indep, 0.3, color=BLUE, alpha=0.6, label="Occupancy (indep.)")
ax1.bar(x + 0.15, occ_resort, 0.3, color=ORANGE, alpha=0.6, label="Occupancy (resort)")
ax1.set_ylabel("Occupancy (%)", color=BLUE)
ax1.set_ylim(0, 100)
ax2 = ax1.twinx()
ax2.plot(x, rates, "o-", color=GREEN, linewidth=2, label="Nightly rate (NOK)")
ax2.set_ylabel("Nightly rate (NOK)", color=GREEN)
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
ax1.set_xticks(x)
ax1.set_xticklabels(months)
ax1.set_title("Kragerø Resort – Occupancy & Nightly Rate by Month", fontsize=14)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
plt.tight_layout()
plt.savefig("output/kragero_occupancy_rates.png", dpi=150)
plt.close()
print("Saved: output/kragero_occupancy_rates.png")

# Chart 3: Annual P&L waterfall – Independent management
fig, ax = plt.subplots(figsize=(14, 6))
labels = ["Gross\nIncome", "Platform\nFees", "Cleaning &\nLaundry", "Other\nOp Costs",
          "Property\nCosts", "Loan\nPayments", "Tax", "Interest\nDeduction",
          "Post-tax\nCashflow"]
values = [
    summary_indep.total_gross_income,
    -summary_indep.platform_fees,
    -(summary_indep.cleaning_costs + summary_indep.laundry_costs + summary_indep.consumable_costs),
    -(summary_indep.furnishing_refresh + summary_indep.marketing_costs + summary_indep.property_management_fees),
    -summary_indep.total_property_costs,
    -summary_indep.annual_loan_payment,
    -summary_indep.rental_income_tax,
    summary_indep.interest_tax_deduction,
    summary_indep.post_tax_cashflow,
]

running = 0
bottoms = []
colors = []
for i, v in enumerate(values):
    if i == len(values) - 1:
        bottoms.append(0)
        colors.append(GREEN if v >= 0 else RED)
    else:
        bottoms.append(running if v >= 0 else running + v)
        colors.append(BLUE if v >= 0 else ORANGE)
        running += v

ax.bar(labels, [abs(v) for v in values], bottom=bottoms, color=colors, width=0.6,
       edgecolor="white", linewidth=0.5)

for i, (v, b) in enumerate(zip(values, bottoms)):
    y = b + abs(v) / 2
    sign = "+" if v >= 0 else ""
    ax.text(i, y, f"{sign}{format_nok(v)}", ha="center", va="center", fontsize=8, fontweight="bold")

ax.set_title("Kragerø Resort – Annual P&L Waterfall (Independent Mgmt, 30 nights own use)", fontsize=13)
ax.set_ylabel("NOK")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
plt.tight_layout()
plt.savefig("output/kragero_waterfall.png", dpi=150)
plt.close()
print("Saved: output/kragero_waterfall.png")

# Chart 4: Scenario comparison bars
fig, ax = plt.subplots(figsize=(14, 5))
scenario_names = list(results.keys())
cashflows = [results[n].post_tax_cashflow for n in scenario_names]
nois = [results[n].net_operating_income for n in scenario_names]
x = np.arange(len(scenario_names))
ax.bar(x - 0.2, nois, 0.4, label="NOI", color=BLUE)
ax.bar(x + 0.2, cashflows, 0.4, label="Post-tax Cashflow", color=GREEN)
ax.set_xticks(x)
ax.set_xticklabels(scenario_names, fontsize=9)
ax.axhline(y=0, color="black", linewidth=0.8)
ax.set_title("Kragerø Resort – Scenario Comparison: NOI & Post-tax Cashflow", fontsize=14)
ax.set_ylabel("NOK")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
ax.legend()
for i, (noi_v, cf_v) in enumerate(zip(nois, cashflows)):
    ax.text(i - 0.2, noi_v + (2000 if noi_v >= 0 else -5000), format_nok(noi_v),
            ha="center", va="bottom" if noi_v >= 0 else "top", fontsize=8)
    ax.text(i + 0.2, cf_v + (2000 if cf_v >= 0 else -5000), format_nok(cf_v),
            ha="center", va="bottom" if cf_v >= 0 else "top", fontsize=8)
plt.tight_layout()
plt.savefig("output/kragero_scenario_comparison.png", dpi=150)
plt.close()
print("Saved: output/kragero_scenario_comparison.png")

# Chart 5: Independent vs Resort pool – side-by-side summary
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for idx, (title, summary, color) in enumerate([
    ("Independent Management", summary_indep, BLUE),
    ("Resort Pool (~30% commission)", summary_resort, ORANGE),
]):
    ax = axes[idx]
    categories = ["Gross\nIncome", "Op\nCosts", "Property\nCosts", "NOI",
                  "Loan\nPayments", "Post-tax\nCashflow"]
    vals = [
        summary.total_gross_income,
        -summary.total_operating_costs,
        -summary.total_property_costs,
        summary.net_operating_income,
        -summary.annual_loan_payment,
        summary.post_tax_cashflow,
    ]
    bar_colors = [GREEN if v >= 0 else RED for v in vals]
    ax.bar(categories, vals, color=bar_colors, alpha=0.8, edgecolor="white")
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_ylabel("NOK")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
    for i, v in enumerate(vals):
        ax.text(i, v + (3000 if v >= 0 else -3000), format_nok(v),
                ha="center", va="bottom" if v >= 0 else "top", fontsize=8)

fig.suptitle("Kragerø Resort – Management Model Comparison (30 nights own use)", fontsize=14)
plt.tight_layout()
plt.savefig("output/kragero_management_comparison.png", dpi=150)
plt.close()
print("Saved: output/kragero_management_comparison.png")

print("\nAll charts saved to output/")
