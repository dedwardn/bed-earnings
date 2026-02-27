"""Generate example output for 5.5M NOK, 25y, 5%, 200k rental income."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os

from norwegian_loan_calculator import (
    LoanParameters,
    RentalParameters,
    compare_loans,
    format_nok,
)

os.makedirs("output", exist_ok=True)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
loan = LoanParameters(
    principal=5_500_000,
    annual_interest_rate=0.05,
    term_years=25,
    extra_fees_per_month=50,
)

rental = RentalParameters(
    monthly_rental_income=200_000 / 12,
    is_short_term=False,
    owner_occupies_half=True,
    annual_maintenance_cost=0,
)

annuity, serial = compare_loans(loan, rental)
months = [mp.month for mp in annuity.monthly_payments]

# ---------------------------------------------------------------------------
# Print KPIs
# ---------------------------------------------------------------------------
print("=" * 90)
print("  EXAMPLE: 5 500 000 NOK | 25 years | 5.0% | 200 000 NOK/yr rental (tax-free)")
print("=" * 90)
print()
print(f"{'Metric':<35s} {'Annuity':>18s} {'Serial':>18s} {'Difference':>18s}")
print("-" * 91)

rows = [
    ("First monthly payment", annuity.monthly_payments[0].total_payment, serial.monthly_payments[0].total_payment),
    ("Last monthly payment", annuity.monthly_payments[-1].total_payment, serial.monthly_payments[-1].total_payment),
    ("Total paid", annuity.total_paid, serial.total_paid),
    ("Total interest", annuity.total_interest, serial.total_interest),
    ("Total fees", annuity.total_fees, serial.total_fees),
    ("Tax deduction (22%)", annuity.total_tax_deduction, serial.total_tax_deduction),
    ("Net cost (after tax ded.)", annuity.total_net_cost, serial.total_net_cost),
    ("", 0, 0),
    ("Rental income (gross)", annuity.total_rental_income_gross, serial.total_rental_income_gross),
    ("Rental tax", annuity.total_rental_tax, serial.total_rental_tax),
    ("Rental income (net)", annuity.total_rental_income_net, serial.total_rental_income_net),
    ("Net cost after rental", annuity.total_net_cost_after_rental, serial.total_net_cost_after_rental),
]

for label, a_val, s_val in rows:
    if not label:
        print()
        continue
    print(f"  {label:<33s} {format_nok(a_val):>18s} {format_nok(s_val):>18s} {format_nok(a_val - s_val):>18s}")

print()

# ---------------------------------------------------------------------------
# Annual schedule tables
# ---------------------------------------------------------------------------
for summary in [annuity, serial]:
    print(f"\n  Annual Schedule — {summary.loan_type} Loan")
    print(f"  {'Year':>4s}  {'Principal':>12s}  {'Interest':>12s}  {'Fees':>10s}"
          f"  {'Total Paid':>12s}  {'Tax Ded.':>12s}  {'Net Cost':>12s}"
          f"  {'Rental Net':>12s}  {'Net-Rental':>12s}  {'Balance':>14s}")
    print("  " + "-" * 128)
    for a in summary.annual_summaries:
        print(f"  {a.year:>4d}  {format_nok(a.total_principal):>12s}  {format_nok(a.total_interest):>12s}"
              f"  {format_nok(a.total_fees):>10s}  {format_nok(a.total_payments):>12s}"
              f"  {format_nok(a.tax_deduction):>12s}  {format_nok(a.net_cost):>12s}"
              f"  {format_nok(a.rental_income_net):>12s}  {format_nok(a.net_cost_after_rental):>12s}"
              f"  {format_nok(a.remaining_balance):>14s}")
    print()

# ---------------------------------------------------------------------------
# Styling helper
# ---------------------------------------------------------------------------
def nok_formatter(x, _):
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"{x/1_000:.0f}k"
    return f"{x:.0f}"

BLUE = "#2196F3"
ORANGE = "#FF7043"
plt.style.use("seaborn-v0_8-whitegrid")

# ---------------------------------------------------------------------------
# Chart 1: Monthly Payments
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(months, [mp.total_payment for mp in annuity.monthly_payments],
        label="Annuity", color=BLUE, linewidth=2)
ax.plot(months, [mp.total_payment for mp in serial.monthly_payments],
        label="Serial", color=ORANGE, linewidth=2)
ax.set_title("Monthly Payment Over Time (5.5M NOK, 5%, 25yr)", fontsize=14)
ax.set_xlabel("Month")
ax.set_ylabel("Payment (NOK)")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_formatter))
ax.legend()
plt.tight_layout()
plt.savefig("output/1_monthly_payments.png", dpi=150)
plt.close()
print("Saved: output/1_monthly_payments.png")

# ---------------------------------------------------------------------------
# Chart 2: Remaining Balance
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 5))
ax.fill_between(months, [mp.remaining_balance for mp in annuity.monthly_payments],
                alpha=0.3, color=BLUE)
ax.plot(months, [mp.remaining_balance for mp in annuity.monthly_payments],
        label="Annuity", color=BLUE, linewidth=2)
ax.fill_between(months, [mp.remaining_balance for mp in serial.monthly_payments],
                alpha=0.3, color=ORANGE)
ax.plot(months, [mp.remaining_balance for mp in serial.monthly_payments],
        label="Serial", color=ORANGE, linewidth=2)
ax.set_title("Remaining Loan Balance", fontsize=14)
ax.set_xlabel("Month")
ax.set_ylabel("Balance (NOK)")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_formatter))
ax.legend()
plt.tight_layout()
plt.savefig("output/2_remaining_balance.png", dpi=150)
plt.close()
print("Saved: output/2_remaining_balance.png")

# ---------------------------------------------------------------------------
# Chart 3: Interest vs Principal (stacked bars)
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

for ax, summary, title in [(ax1, annuity, "Annuity"), (ax2, serial, "Serial")]:
    years = [a.year for a in summary.annual_summaries]
    principals = [a.total_principal for a in summary.annual_summaries]
    interests = [a.total_interest for a in summary.annual_summaries]
    ax.bar(years, principals, label="Principal", color=BLUE, width=0.8)
    ax.bar(years, interests, bottom=principals, label="Interest", color=ORANGE, width=0.8)
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_formatter))
    ax.legend(fontsize=9)

ax1.set_ylabel("NOK")
fig.suptitle("Annual Principal vs Interest Breakdown", fontsize=14)
plt.tight_layout()
plt.savefig("output/3_interest_vs_principal.png", dpi=150)
plt.close()
print("Saved: output/3_interest_vs_principal.png")

# ---------------------------------------------------------------------------
# Chart 4: Cumulative Cost
# ---------------------------------------------------------------------------
ann_cum_gross = list(np.cumsum([mp.total_payment for mp in annuity.monthly_payments]))
ann_cum_net = list(np.cumsum([mp.net_payment for mp in annuity.monthly_payments]))
ser_cum_gross = list(np.cumsum([mp.total_payment for mp in serial.monthly_payments]))
ser_cum_net = list(np.cumsum([mp.net_payment for mp in serial.monthly_payments]))

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(months, ann_cum_gross, label="Annuity (gross)", color=BLUE, linestyle="--", alpha=0.5)
ax.plot(months, ann_cum_net, label="Annuity (net after tax ded.)", color=BLUE, linewidth=2.5)
ax.plot(months, ser_cum_gross, label="Serial (gross)", color=ORANGE, linestyle="--", alpha=0.5)
ax.plot(months, ser_cum_net, label="Serial (net after tax ded.)", color=ORANGE, linewidth=2.5)
ax.set_title("Cumulative Cost — Gross vs Net (after 22% interest deduction)", fontsize=14)
ax.set_xlabel("Month")
ax.set_ylabel("Cumulative cost (NOK)")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_formatter))
ax.legend()
plt.tight_layout()
plt.savefig("output/4_cumulative_cost.png", dpi=150)
plt.close()
print("Saved: output/4_cumulative_cost.png")

# ---------------------------------------------------------------------------
# Chart 5: Annual Net Cost After Rental
# ---------------------------------------------------------------------------
years = [a.year for a in annuity.annual_summaries]
ann_net = [a.net_cost_after_rental for a in annuity.annual_summaries]
ser_net = [a.net_cost_after_rental for a in serial.annual_summaries]

fig, ax = plt.subplots(figsize=(12, 5))
x = np.array(years)
w = 0.35
ax.bar(x - w/2, ann_net, w, label="Annuity", color=BLUE)
ax.bar(x + w/2, ser_net, w, label="Serial", color=ORANGE)
ax.set_title("Annual Net Cost After Rental Income (200k/yr tax-free)", fontsize=14)
ax.set_xlabel("Year")
ax.set_ylabel("NOK")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_formatter))
ax.legend()
plt.tight_layout()
plt.savefig("output/5_annual_net_cost_after_rental.png", dpi=150)
plt.close()
print("Saved: output/5_annual_net_cost_after_rental.png")

# ---------------------------------------------------------------------------
# Chart 6: Rate Sensitivity
# ---------------------------------------------------------------------------
rates = np.arange(0.02, 0.08, 0.005)
ann_costs, ser_costs = [], []
for r in rates:
    test_loan = LoanParameters(principal=5_500_000, annual_interest_rate=r,
                               term_years=25, extra_fees_per_month=50)
    a, s = compare_loans(test_loan, rental)
    ann_costs.append(a.total_net_cost)
    ser_costs.append(s.total_net_cost)

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot([r*100 for r in rates], ann_costs, "o-", label="Annuity", color=BLUE, linewidth=2)
ax.plot([r*100 for r in rates], ser_costs, "o-", label="Serial", color=ORANGE, linewidth=2)
ax.axvline(x=5.0, linestyle="--", color="gray", alpha=0.7, label="Current rate (5%)")
ax.set_title("Total Net Cost vs Interest Rate (5.5M NOK, 25yr)", fontsize=14)
ax.set_xlabel("Annual interest rate (%)")
ax.set_ylabel("Total net cost (NOK)")
ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_formatter))
ax.xaxis.set_major_formatter(ticker.PercentFormatter(xmax=100, decimals=1))
ax.legend()
plt.tight_layout()
plt.savefig("output/6_rate_sensitivity.png", dpi=150)
plt.close()
print("Saved: output/6_rate_sensitivity.png")

print("\nAll 6 charts saved to output/")
