"""
Wealth-building comparison: Resort apartment vs alternative investments.

Compares net wealth impact over 5-25 years, accounting for:
- Leverage amplification on real estate
- Property appreciation
- Loan principal paydown (forced savings)
- Monthly cashflow deficit as opportunity cost
- Alternative returns if same cash was invested elsewhere
- Norwegian tax on capital gains (aksjesparekonto, exit tax, etc.)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os

# ============================================================================
# ASSUMPTIONS
# ============================================================================

PROPERTY_VALUE = 3_578_340       # Totalpris
YEARS = 25

# --- Apartment scenarios ---
APT_SCENARIOS = {
    "Apt 100% LTV, 5%": {
        "loan_amount": 3_578_340,
        "rate": 0.05,
        "equity_in": 0,
        "annual_cashflow": -100_042,  # post-tax cashflow from model
        "appreciation": 0.03,         # 3% annual property appreciation
    },
    "Apt 100% LTV, 6%": {
        "loan_amount": 3_578_340,
        "rate": 0.06,
        "equity_in": 0,
        "annual_cashflow": -117_810,
        "appreciation": 0.03,
    },
    "Apt 75% LTV, 5%": {
        "loan_amount": 2_683_755,
        "rate": 0.05,
        "equity_in": 894_585,
        "annual_cashflow": -47_126,
        "appreciation": 0.03,
    },
}

# --- Alternative investments ---
# If you DON'T buy the apartment, what happens to:
# (a) The equity you would have put in (894k for 75% LTV, 0 for 100%)
# (b) The monthly cashflow you save (you'd invest it instead)
#
# Norwegian tax on stock gains:
# - Aksjesparekonto (ASK): tax-deferred, 37.84% on withdrawal (2025 effective rate)
# - Regular account: 37.84% on realized gains annually or at exit
# - Real estate: primary home tax-free after 1yr, secondary/leisure: 22% on gains
#   (but leisure property gains rarely taxed if owned 1yr+ and used as fritidsbolig)

STOCK_TAX_RATE = 0.3784          # Effective tax on stock gains (ASK withdrawal)
PROPERTY_GAINS_TAX = 0.22        # On leisure property if sold (often avoidable)

ALT_SCENARIOS = {
    "Global index 7%": {"annual_return": 0.07},
    "Global index 5%": {"annual_return": 0.05},
    "Bonds/savings 3.5%": {"annual_return": 0.035},
}

PROPERTY_APPRECIATION_RATES = [0.02, 0.03, 0.04]  # sensitivity


def annuity_schedule(loan, rate, years):
    """Return list of (interest, principal, remaining) per year."""
    mr = rate / 12
    n = years * 12
    if mr > 0:
        monthly = loan * (mr * (1 + mr)**n) / ((1 + mr)**n - 1)
    else:
        monthly = loan / n
    
    schedule = []
    remaining = loan
    for year in range(1, years + 1):
        year_interest = 0
        year_principal = 0
        for _ in range(12):
            interest = remaining * mr
            principal = monthly - interest
            remaining -= principal
            year_interest += interest
            year_principal += principal
        schedule.append({
            "year": year,
            "interest": year_interest,
            "principal": year_principal,
            "remaining": max(0, remaining),
            "total_paid": year_interest + year_principal,
        })
    return schedule


def simulate_apartment(scenario, years, appreciation):
    """Simulate apartment wealth over time."""
    sched = annuity_schedule(scenario["loan_amount"], scenario["rate"], 25)
    
    equity_in = scenario["equity_in"]
    annual_cf = scenario["annual_cashflow"]
    
    results = []
    cumulative_cash_out = equity_in  # initial equity is cash out
    
    for y in range(1, years + 1):
        if y <= len(sched):
            s = sched[y - 1]
            remaining_loan = s["remaining"]
        else:
            remaining_loan = 0
        
        property_value = PROPERTY_VALUE * (1 + appreciation) ** y
        cumulative_cash_out += abs(annual_cf) if annual_cf < 0 else -annual_cf
        
        # Net wealth = property value - remaining loan
        gross_equity = property_value - remaining_loan
        
        # If sold: gains tax on appreciation (conservative - include it)
        purchase_basis = PROPERTY_VALUE
        gain = property_value - purchase_basis
        tax_on_sale = max(0, gain * PROPERTY_GAINS_TAX)
        
        net_wealth_after_tax = gross_equity - tax_on_sale
        
        # Total return = net wealth - total cash invested
        total_cash_invested = equity_in + abs(annual_cf) * y if annual_cf < 0 else equity_in
        net_return = net_wealth_after_tax - total_cash_invested
        
        # Principal paid so far
        total_principal = sum(sched[i]["principal"] for i in range(min(y, len(sched))))
        
        results.append({
            "year": y,
            "property_value": property_value,
            "remaining_loan": remaining_loan,
            "gross_equity": gross_equity,
            "net_wealth": net_wealth_after_tax,
            "cumulative_cash_out": cumulative_cash_out,
            "total_principal_paid": total_principal,
            "appreciation_gain": property_value - PROPERTY_VALUE,
            "net_return": net_return,
        })
    
    return results


def simulate_alternative(annual_cf_saved, equity_saved, annual_return, years):
    """Simulate investing saved cashflow + equity in stocks/bonds."""
    portfolio = equity_saved
    results = []
    
    monthly_invest = abs(annual_cf_saved) / 12 if annual_cf_saved < 0 else 0
    monthly_return = (1 + annual_return) ** (1/12) - 1
    
    for y in range(1, years + 1):
        # Invest monthly throughout the year
        for _ in range(12):
            portfolio = portfolio * (1 + monthly_return) + monthly_invest
        
        total_invested = equity_saved + abs(annual_cf_saved) * y if annual_cf_saved < 0 else equity_saved
        gain = portfolio - total_invested
        tax = max(0, gain * STOCK_TAX_RATE)
        net_after_tax = portfolio - tax
        
        results.append({
            "year": y,
            "portfolio_value": portfolio,
            "total_invested": total_invested,
            "gain_pretax": gain,
            "tax_on_exit": tax,
            "net_after_tax": net_after_tax,
            "net_return": net_after_tax - total_invested,
        })
    
    return results


# ============================================================================
# RUN ANALYSIS
# ============================================================================

print("=" * 100)
print("  WEALTH-BUILDING COMPARISON: RESORT APARTMENT vs ALTERNATIVE INVESTMENTS")
print("  Kragerø Resort 633/634 | 30 nights own use | Independent Airbnb management")
print("=" * 100)

# --- Main comparison: 100% LTV @ 5% vs investing the cashflow deficit ---
print("\n" + "=" * 100)
print("  SCENARIO: 100% financed @ 5%, 3% property appreciation")
print("  vs investing the same monthly outlay in stocks/bonds")
print("=" * 100)

apt = APT_SCENARIOS["Apt 100% LTV, 5%"]
apt_results = simulate_apartment(apt, YEARS, 0.03)

print(f"\n  Apartment: 0 kr equity in, {abs(apt['annual_cashflow']):,.0f} kr/year cashflow deficit")
print(f"  Alternative: invest the {abs(apt['annual_cashflow']):,.0f} kr/year instead\n")

milestones = [5, 10, 15, 20, 25]
header = f"  {'Year':<6s} {'Prop Value':>12s} {'Loan Left':>12s} {'Apt Equity':>12s} {'Cash In':>12s}"
for alt_name in ALT_SCENARIOS:
    header += f" {alt_name:>16s}"
header += f" {'Apt Advantage':>16s}"
print(header)
print("  " + "-" * (len(header) - 2))

for y in milestones:
    ar = apt_results[y - 1]
    line = f"  {y:<6d} {ar['property_value']:>12,.0f} {ar['remaining_loan']:>12,.0f} {ar['net_wealth']:>12,.0f} {ar['cumulative_cash_out']:>12,.0f}"
    
    alt_nets = []
    for alt_name, alt_params in ALT_SCENARIOS.items():
        alt_r = simulate_alternative(apt["annual_cashflow"], 0, alt_params["annual_return"], y)
        net = alt_r[-1]["net_after_tax"]
        alt_nets.append(net)
        line += f" {net:>16,.0f}"
    
    best_alt = max(alt_nets)
    advantage = ar["net_wealth"] - best_alt
    line += f" {advantage:>+16,.0f}"
    print(line)

# --- Breakdown of where apartment wealth comes from ---
print(f"\n\n  APARTMENT WEALTH BREAKDOWN (100% LTV @ 5%, 3% appreciation)")
print("  " + "-" * 80)
print(f"  {'Year':<6s} {'Appreciation':>14s} {'Principal Paid':>15s} {'Total Equity':>14s} {'Cash Invested':>14s} {'Net Return':>14s}")
print("  " + "-" * 80)

for y in milestones:
    ar = apt_results[y - 1]
    print(f"  {y:<6d} {ar['appreciation_gain']:>+14,.0f} {ar['total_principal_paid']:>15,.0f} {ar['net_wealth']:>14,.0f} {ar['cumulative_cash_out']:>14,.0f} {ar['net_return']:>+14,.0f}")

# --- Sensitivity: different appreciation rates ---
print(f"\n\n  SENSITIVITY: NET WEALTH AT YEAR 10 by appreciation rate & interest rate")
print("  " + "-" * 80)
header = f"  {'Scenario':<25s}"
for apr in PROPERTY_APPRECIATION_RATES:
    header += f" {'Prop ' + f'{apr*100:.0f}%':>14s}"
for alt_name in ALT_SCENARIOS:
    header += f" {alt_name:>16s}"
print(header)
print("  " + "-" * (len(header) - 2))

for apt_name, apt_params in APT_SCENARIOS.items():
    line = f"  {apt_name:<25s}"
    for apr in PROPERTY_APPRECIATION_RATES:
        r = simulate_apartment(apt_params, 10, apr)
        line += f" {r[-1]['net_wealth']:>14,.0f}"
    print(line)

# Alternatives row (same regardless - they invest the 100% LTV 5% cashflow)
line = f"  {'Alternatives (vs 100%/5%)':<25s}"
line += f" {'':>14s}" * len(PROPERTY_APPRECIATION_RATES)
print(line)
for alt_name, alt_params in ALT_SCENARIOS.items():
    line = f"  {' → ' + alt_name:<25s}"
    line += f" {'':>14s}" * len(PROPERTY_APPRECIATION_RATES)
    alt_r = simulate_alternative(APT_SCENARIOS["Apt 100% LTV, 5%"]["annual_cashflow"], 0, alt_params["annual_return"], 10)
    line += f" {alt_r[-1]['net_after_tax']:>16,.0f}"
    # pad remaining
    line += f" {'':>16s}" * (len(ALT_SCENARIOS) - 1)
    print(line)

# --- The real comparison: 75% LTV where you CHOOSE where to put 895k ---
print(f"\n\n  COMPARISON: 75% LTV (895k equity in apartment) vs 100% index fund")
print("  " + "-" * 80)
print(f"  If you have 895k cash + can absorb ~4k/month deficit:")
print(f"  Option A: Put 895k in apartment equity, pay 3,927 kr/mo deficit")
print(f"  Option B: Put 895k in index fund, pay 0 kr/mo (no apartment)")
print(f"  Option C: Finance 100%, put 0 in apartment, invest savings elsewhere\n")

apt_75 = APT_SCENARIOS["Apt 75% LTV, 5%"]
apt_100 = APT_SCENARIOS["Apt 100% LTV, 5%"]

print(f"  {'Year':<6s} {'A: 75% LTV apt':>16s} {'B: 895k stocks':>16s} {'C: 100%+stocks':>16s} {'A vs B':>14s} {'C vs B':>14s}")
print("  " + "-" * 84)

for y in milestones:
    # Option A: 75% LTV apartment
    a_results = simulate_apartment(apt_75, y, 0.03)
    a_wealth = a_results[-1]["net_wealth"]
    
    # Option B: 895k in index fund, no apartment, no monthly cost
    b_results = simulate_alternative(0, 894_585, 0.07, y)
    b_wealth = b_results[-1]["net_after_tax"]
    
    # Option C: 100% LTV apartment + invest saved cashflow difference
    c_apt = simulate_apartment(apt_100, y, 0.03)
    c_apt_wealth = c_apt[-1]["net_wealth"]
    # Save the difference: 100% costs 100k/yr, 75% costs 47k/yr
    # But with 100%, you also have 895k free + save the 47k/yr vs option A
    # Actually: compare to B. In C you have apartment + stocks from not putting 895k in
    # Monthly savings vs option A = you keep the 895k and invest it
    c_stock = simulate_alternative(0, 894_585, 0.07, y)
    c_total = c_apt_wealth + c_stock[-1]["net_after_tax"]
    
    print(f"  {y:<6d} {a_wealth:>16,.0f} {b_wealth:>16,.0f} {c_total:>16,.0f} {a_wealth - b_wealth:>+14,.0f} {c_total - b_wealth:>+14,.0f}")

print(f"\n  Note: Option C = apartment (100% financed) + 895k in global index @ 7%")
print(f"  Option B = no apartment, just stocks. A vs B shows apartment + own use value.")


# --- Key insight ---
print(f"\n\n{'=' * 100}")
print("  KEY INSIGHTS")
print("=" * 100)
apt10 = simulate_apartment(apt_100, 10, 0.03)[-1]
alt10 = simulate_alternative(apt_100["annual_cashflow"], 0, 0.07, 10)[-1]
print(f"""
  1. LEVERAGE IS THE SUPERPOWER
     With 0 kr equity, 3% appreciation on 3.58M = 107k/yr in paper gains (year 1).
     That's leveraged return on... nothing. You can't get that in stocks without margin.

  2. AFTER 10 YEARS (100% LTV, 5%, 3% appreciation):
     Property value:  {apt10['property_value']:>12,.0f} kr  (up {apt10['appreciation_gain']:>+,.0f})
     Loan remaining:  {apt10['remaining_loan']:>12,.0f} kr
     Your equity:     {apt10['net_wealth']:>12,.0f} kr
     Cash invested:   {apt10['cumulative_cash_out']:>12,.0f} kr  (your deficit payments)
     Net return:      {apt10['net_return']:>+12,.0f} kr

  3. VS STOCKS (same cash invested in global index @ 7%):
     Portfolio:       {alt10['net_after_tax']:>12,.0f} kr  (after 37.84% exit tax)
     Cash invested:   {alt10['total_invested']:>12,.0f} kr
     Net return:      {alt10['net_return']:>+12,.0f} kr

  4. THE APARTMENT ADVANTAGE: you also GET TO USE IT 30 nights/year.
     That's ~{30*10} hotel nights over 10 years you didn't pay for separately.
     At 1,500-3,000 kr/night for comparable accommodation, that's
     ~{30*10*2000:,} kr of "free" holiday value.

  5. RISK DIFFERENCES:
     - Apartment: illiquid, concentrated, maintenance risk, rate risk
     - Stocks: liquid, diversified, volatile short-term, no effort
     - Apartment has FORCED SAVINGS via principal repayment
     - If rates rise to 7%+, apartment cashflow gets painful
""")

# ============================================================================
# CHARTS
# ============================================================================
os.makedirs("output", exist_ok=True)

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

# Chart: Wealth trajectory over 25 years
fig, ax = plt.subplots(figsize=(14, 7))
years_range = list(range(1, YEARS + 1))

# Apartment scenarios
for apr_rate, style in [(0.02, "--"), (0.03, "-"), (0.04, ":")]:
    results = simulate_apartment(APT_SCENARIOS["Apt 100% LTV, 5%"], YEARS, apr_rate)
    wealth = [r["net_wealth"] for r in results]
    ax.plot(years_range, wealth, style, color=BLUE, linewidth=2,
            label=f"Apartment 100% LTV 5%, {apr_rate*100:.0f}% appr.", alpha=0.8)

# Stock alternatives (investing same cashflow)
cf = APT_SCENARIOS["Apt 100% LTV, 5%"]["annual_cashflow"]
for alt_name, alt_params, color in [
    ("Global index 7%", ALT_SCENARIOS["Global index 7%"], GREEN),
    ("Global index 5%", ALT_SCENARIOS["Global index 5%"], ORANGE),
    ("Bonds 3.5%", ALT_SCENARIOS["Bonds/savings 3.5%"], PURPLE),
]:
    results = simulate_alternative(cf, 0, alt_params["annual_return"], YEARS)
    wealth = [r["net_after_tax"] for r in results]
    ax.plot(years_range, wealth, "-", color=color, linewidth=2, label=alt_name)

ax.axhline(y=0, color="black", linewidth=0.5)
ax.set_xlabel("Years", fontsize=12)
ax.set_ylabel("Net Wealth (NOK)", fontsize=12)
ax.set_title("Wealth Building: Apartment (100% financed, 5%) vs Stocks/Bonds\n"
             "Same monthly outlay (~8,300 kr/mo) invested in each", fontsize=14)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
ax.legend(loc="upper left", fontsize=9)
ax.set_xlim(1, YEARS)
plt.tight_layout()
plt.savefig("output/kragero_wealth_comparison.png", dpi=150)
plt.close()
print("\nSaved: output/kragero_wealth_comparison.png")

# Chart 2: Apartment equity breakdown (stacked)
fig, ax = plt.subplots(figsize=(14, 6))
results_3pct = simulate_apartment(APT_SCENARIOS["Apt 100% LTV, 5%"], YEARS, 0.03)
appreciation = [r["appreciation_gain"] for r in results_3pct]
principal = [r["total_principal_paid"] for r in results_3pct]
cash_out = [r["cumulative_cash_out"] for r in results_3pct]
net_wealth = [r["net_wealth"] for r in results_3pct]

ax.fill_between(years_range, 0, principal, alpha=0.6, color=BLUE, label="Principal paid (forced savings)")
ax.fill_between(years_range, principal, [p+a for p,a in zip(principal, appreciation)],
                alpha=0.6, color=GREEN, label="Appreciation gain (3%/yr)")
ax.plot(years_range, cash_out, "--", color=RED, linewidth=2, label="Cumulative cash invested")
ax.plot(years_range, net_wealth, "-", color="black", linewidth=2.5, label="Net wealth (after sale tax)")

ax.set_xlabel("Years", fontsize=12)
ax.set_ylabel("NOK", fontsize=12)
ax.set_title("Apartment Equity Breakdown: Where the Wealth Comes From\n"
             "100% financed @ 5%, 3% annual appreciation", fontsize=14)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
ax.legend(loc="upper left")
plt.tight_layout()
plt.savefig("output/kragero_equity_breakdown.png", dpi=150)
plt.close()
print("Saved: output/kragero_equity_breakdown.png")

print("\nAll charts saved to output/")
