"""
Example: Kragerø Resort Apartment Investment Analysis
=====================================================

Based on Finn listing 461543499 – Stabbestadveien 1, Kragerø Resort 207/307
(Krogsveen listing). 2 bedrooms, 2 bathrooms, 3 terraces, sea view,
boat berth, golf rights. Sold fully furnished.

Pricing estimates from Airbnb/Booking.com comparable listings in the area:
- Peak summer (Jun-Aug): ~2,000-2,500 NOK/night
- Shoulder (May, Sep): ~1,200-1,500 NOK/night
- Low season (Oct-Apr): ~800-1,000 NOK/night
- Coastal resort occupancy: ~70% summer, ~40% shoulder, ~15-20% winter

Sources:
- Krogsveen listing: Stabbestadveien 1, unit 207/307
- Airbnb comparable listings in Kragerø area
- Booking.com Kragerø Resort rates
- Hotels.com / Momondo average: $114-$233/night (~1,200-2,500 NOK)
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

os.makedirs("output", exist_ok=True)

# ---------------------------------------------------------------------------
# Property: Kragerø Resort 207/307
# ---------------------------------------------------------------------------
kragero = PropertyDetails(
    name="Kragerø Resort 207/307 – Stabbestadveien 1",
    purchase_price=3_900_000,        # Estimated total price with costs
    sqm=70,                          # ~70 sqm estimated
    bedrooms=2,
    bathrooms=2,
    monthly_fees=9_723,              # ~116,676 kr/year ÷ 12
    annual_property_tax=0,           # Fritidsbolig often exempt in Kragerø
    annual_insurance=8_000,
    annual_maintenance=15_000,
    annual_utilities=18_000,         # Strøm, internett, TV
    formuesverdi=800_000,            # Estimated
)

# ---------------------------------------------------------------------------
# Pricing Model 1: High/Low Season (simple)
# ---------------------------------------------------------------------------
high_low_pricing = HighLowSeasonPricing(
    high_season_nightly_rate=2_200,    # Jun-Aug
    low_season_nightly_rate=900,       # Oct-Apr
    shoulder_nightly_rate=1_400,       # May, Sep
    high_season_months=3,
    shoulder_season_months=2,
    high_season_occupancy=0.70,
    low_season_occupancy=0.15,
    shoulder_occupancy=0.40,
    cleaning_fee_per_stay=800,
    avg_stay_nights=3.5,
)

# ---------------------------------------------------------------------------
# Pricing Model 2: Month-by-month variable pricing
# ---------------------------------------------------------------------------
monthly_pricing = MonthlyPricing(
    months=[
        {"month": "Jan", "nightly_rate": 800,   "occupancy": 0.10},  # Dead season
        {"month": "Feb", "nightly_rate": 1_000,  "occupancy": 0.20},  # Winter holiday
        {"month": "Mar", "nightly_rate": 900,   "occupancy": 0.12},  # Easter can spike
        {"month": "Apr", "nightly_rate": 1_000,  "occupancy": 0.15},  # Easter/spring
        {"month": "May", "nightly_rate": 1_300,  "occupancy": 0.35},  # Shoulder
        {"month": "Jun", "nightly_rate": 2_000,  "occupancy": 0.60},  # Early summer
        {"month": "Jul", "nightly_rate": 2_500,  "occupancy": 0.85},  # Peak
        {"month": "Aug", "nightly_rate": 2_200,  "occupancy": 0.65},  # Late summer
        {"month": "Sep", "nightly_rate": 1_400,  "occupancy": 0.35},  # Shoulder
        {"month": "Oct", "nightly_rate": 1_000,  "occupancy": 0.15},  # Autumn
        {"month": "Nov", "nightly_rate": 800,   "occupancy": 0.08},  # Low
        {"month": "Dec", "nightly_rate": 1_200,  "occupancy": 0.25},  # Christmas/NYE
    ],
    cleaning_fee_per_stay=800,
    avg_stay_nights=3.5,
)

# ---------------------------------------------------------------------------
# Operating costs
# ---------------------------------------------------------------------------
ops = OperatingCosts(
    platform_commission_rate=0.03,     # Airbnb host fee
    cleaning_cost_per_turnover=900,    # Professional cleaning
    laundry_per_turnover=250,          # Linens
    consumables_per_turnover=150,      # Toiletries, coffee, etc.
    annual_furnishing_refresh=12_000,
    annual_marketing=0,
    property_management_rate=0.0,      # Self-managed
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
print("=" * 80)

# Scenario 1: High/Low model, 30 nights own use
print("\n\n>>> SCENARIO A: High/Low Season Model, 30 nights own use")
summary_hl = calculate_investment(kragero, high_low_pricing, ops, loan, own_use_nights=30)
print_investment_summary(summary_hl, kragero)

# Scenario 2: Monthly variable model, 30 nights own use
print("\n\n>>> SCENARIO B: Monthly Variable Pricing, 30 nights own use")
summary_mv = calculate_investment(kragero, monthly_pricing, ops, loan, own_use_nights=30)
print_investment_summary(summary_mv, kragero)

# ---------------------------------------------------------------------------
# Compare scenarios
# ---------------------------------------------------------------------------
scenarios = {
    "H/L 30 own": (high_low_pricing, 30),
    "Monthly 30 own": (monthly_pricing, 30),
    "Monthly 60 own": (monthly_pricing, 60),
    "Monthly 0 own": (monthly_pricing, 0),
}
results = compare_scenarios(kragero, scenarios, ops, loan)
print_scenario_comparison(results)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
BLUE = "#2196F3"
ORANGE = "#FF7043"
GREEN = "#66BB6A"
plt.style.use("seaborn-v0_8-whitegrid")

def nok_fmt(x, _):
    if abs(x) >= 1_000_000:
        return f"{x/1e6:.1f}M"
    if abs(x) >= 1_000:
        return f"{x/1e3:.0f}k"
    return f"{x:.0f}"

# Chart 1: Monthly revenue breakdown (variable pricing model)
fig, ax = plt.subplots(figsize=(13, 5))
months = [m.month for m in summary_mv.monthly_breakdown]
gross = [m.gross_rental_income for m in summary_mv.monthly_breakdown]
net = [m.net_rental_income for m in summary_mv.monthly_breakdown]
x = np.arange(len(months))
ax.bar(x - 0.2, gross, 0.4, label="Gross rental", color=BLUE)
ax.bar(x + 0.2, net, 0.4, label="Net rental (after op costs)", color=GREEN)
ax.set_xticks(x)
ax.set_xticklabels(months)
ax.set_title("Kragerø Resort – Monthly Revenue (Variable Pricing)", fontsize=14)
ax.set_ylabel("NOK")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
ax.legend()
plt.tight_layout()
plt.savefig("output/kragero_monthly_revenue.png", dpi=150)
plt.close()
print("Saved: output/kragero_monthly_revenue.png")

# Chart 2: Occupancy and nightly rate by month
fig, ax1 = plt.subplots(figsize=(13, 5))
occ = [m.occupancy * 100 for m in summary_mv.monthly_breakdown]
rates = [m.nightly_rate for m in summary_mv.monthly_breakdown]
ax1.bar(x, occ, color=BLUE, alpha=0.6, label="Occupancy %")
ax1.set_ylabel("Occupancy (%)", color=BLUE)
ax1.set_ylim(0, 100)
ax2 = ax1.twinx()
ax2.plot(x, rates, "o-", color=ORANGE, linewidth=2, label="Nightly rate")
ax2.set_ylabel("Nightly rate (NOK)", color=ORANGE)
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

# Chart 3: Annual P&L waterfall
fig, ax = plt.subplots(figsize=(13, 6))
labels = ["Gross\nIncome", "Platform\nFees", "Cleaning", "Other\nOp Costs",
          "Property\nCosts", "Loan\nPayments", "Tax", "Interest\nDeduction",
          "Post-tax\nCashflow"]
values = [
    summary_mv.total_gross_income,
    -summary_mv.platform_fees,
    -(summary_mv.cleaning_costs + summary_mv.laundry_costs + summary_mv.consumable_costs),
    -(summary_mv.furnishing_refresh + summary_mv.marketing_costs + summary_mv.property_management_fees),
    -summary_mv.total_property_costs,
    -summary_mv.annual_loan_payment,
    -summary_mv.rental_income_tax,
    summary_mv.interest_tax_deduction,
    summary_mv.post_tax_cashflow,
]

running = 0
bottoms = []
colors = []
for i, v in enumerate(values):
    if i == len(values) - 1:
        bottoms.append(0)
        colors.append(GREEN if v >= 0 else "#EF5350")
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

ax.set_title("Kragerø Resort – Annual P&L Waterfall (Variable Pricing, 30 nights own use)", fontsize=13)
ax.set_ylabel("NOK")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
plt.tight_layout()
plt.savefig("output/kragero_waterfall.png", dpi=150)
plt.close()
print("Saved: output/kragero_waterfall.png")

# Chart 4: Scenario comparison bars
fig, ax = plt.subplots(figsize=(13, 5))
scenario_names = list(results.keys())
cashflows = [results[n].post_tax_cashflow for n in scenario_names]
nois = [results[n].net_operating_income for n in scenario_names]
x = np.arange(len(scenario_names))
ax.bar(x - 0.2, nois, 0.4, label="NOI", color=BLUE)
ax.bar(x + 0.2, cashflows, 0.4, label="Post-tax Cashflow", color=GREEN)
ax.set_xticks(x)
ax.set_xticklabels(scenario_names)
ax.axhline(y=0, color="black", linewidth=0.8)
ax.set_title("Scenario Comparison – NOI & Post-tax Cashflow", fontsize=14)
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

print("\nAll charts saved to output/")
