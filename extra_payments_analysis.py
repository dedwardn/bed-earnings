"""
Extra Mortgage Payments vs Alternative Investments – Norway
===========================================================

Analyzes whether to put extra money toward your mortgage or invest elsewhere.
Accounts for Norwegian tax rules:
- Rentefradrag: 22% tax deduction on mortgage interest
- Aksjesparekonto: stock gains taxed at effective ~37.84%
- Risk-free comparison after tax adjustments
- Break-even return needed to beat mortgage paydown

Key insight: the effective mortgage cost after rentefradrag is:
  rate × (1 - 0.22) = rate × 0.78
So at 5%, your effective cost is 3.9%. An alternative investment must
return more than 3.9% AFTER TAX to beat paying down the mortgage.
"""

from dataclasses import dataclass
from typing import Optional
import math


# ---------------------------------------------------------------------------
# Norwegian tax constants (2025)
# ---------------------------------------------------------------------------
RENTEFRADRAG_RATE = 0.22
STOCK_GAIN_TAX_RATE = 0.3784       # Aksjesparekonto effective rate (22% × 1.72 oppjustering)
CAPITAL_INCOME_TAX_RATE = 0.22     # Rental income, bank interest, etc.


@dataclass
class MortgageDetails:
    """Current mortgage situation."""
    remaining_balance: float
    annual_interest_rate: float
    remaining_years: int
    loan_type: str = "annuity"     # "annuity" or "serial"
    monthly_fee: float = 0.0       # Termingebyr


@dataclass
class ExtraPaymentScenario:
    """A scenario for extra monthly payments."""
    extra_monthly: float           # Extra NOK per month toward mortgage
    label: str = ""


@dataclass
class AlternativeInvestment:
    """An alternative place to put the money."""
    name: str
    annual_return: float           # Pre-tax nominal return
    tax_rate: float                # Tax on gains at exit
    risk_level: str = "medium"     # "low", "medium", "high"


# ---------------------------------------------------------------------------
# Default alternatives
# ---------------------------------------------------------------------------
DEFAULT_ALTERNATIVES = [
    AlternativeInvestment("Global index fund (ASK)", 0.07, STOCK_GAIN_TAX_RATE, "medium"),
    AlternativeInvestment("Norwegian equity (ASK)", 0.08, STOCK_GAIN_TAX_RATE, "high"),
    AlternativeInvestment("Bond fund", 0.04, CAPITAL_INCOME_TAX_RATE, "low"),
    AlternativeInvestment("High-yield savings", 0.035, CAPITAL_INCOME_TAX_RATE, "low"),
    AlternativeInvestment("Rental property (leveraged)", 0.10, CAPITAL_INCOME_TAX_RATE, "high"),
]


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def calculate_annuity_payment(balance, annual_rate, remaining_months):
    mr = annual_rate / 12
    if mr <= 0:
        return balance / remaining_months
    return balance * (mr * (1 + mr) ** remaining_months) / ((1 + mr) ** remaining_months - 1)


def simulate_mortgage(mortgage: MortgageDetails, extra_monthly: float = 0):
    """
    Simulate mortgage with optional extra payments.
    Extra payments reduce principal; monthly payment stays the same
    (recalculated based on remaining balance and ORIGINAL remaining term).

    Returns month-by-month schedule.
    """
    balance = mortgage.remaining_balance
    mr = mortgage.annual_interest_rate / 12
    total_months = mortgage.remaining_years * 12

    if mortgage.loan_type == "annuity":
        base_payment = calculate_annuity_payment(balance, mortgage.annual_interest_rate, total_months)
    else:
        base_payment = balance / total_months + balance * mr

    schedule = []
    total_interest = 0
    total_principal = 0
    month = 0

    while balance > 0.01 and month < total_months:
        month += 1
        interest = balance * mr

        if mortgage.loan_type == "annuity":
            principal = base_payment - interest
        else:
            principal = mortgage.remaining_balance / total_months

        principal += extra_monthly
        principal = min(principal, balance)

        balance -= principal
        balance = max(0, balance)
        total_interest += interest
        total_principal += principal

        schedule.append({
            "month": month,
            "interest": interest,
            "principal": principal,
            "extra": min(extra_monthly, principal),
            "payment": interest + principal + mortgage.monthly_fee,
            "balance": balance,
            "total_interest_so_far": total_interest,
        })

        if balance <= 0:
            break

        if mortgage.loan_type == "serial":
            pass  # principal stays constant

    return schedule


def simulate_investment(monthly_amount, annual_return, years, tax_rate):
    """Simulate monthly DCA into an investment."""
    monthly_return = (1 + annual_return) ** (1/12) - 1
    portfolio = 0
    total_invested = 0
    schedule = []

    for month in range(1, years * 12 + 1):
        portfolio = portfolio * (1 + monthly_return) + monthly_amount
        total_invested += monthly_amount

        if month % 12 == 0:
            gain = portfolio - total_invested
            tax = max(0, gain * tax_rate)
            schedule.append({
                "year": month // 12,
                "portfolio": portfolio,
                "invested": total_invested,
                "gain_pretax": gain,
                "tax_on_exit": tax,
                "net_after_tax": portfolio - tax,
            })

    return schedule


def analyze_extra_payments(
    mortgage: MortgageDetails,
    extra_amounts: list[float],
    alternatives: Optional[list[AlternativeInvestment]] = None,
    analysis_years: Optional[int] = None,
):
    """
    Full analysis comparing extra mortgage payments vs alternative investments.

    Returns a dict with all results for display/charting.
    """
    if alternatives is None:
        alternatives = DEFAULT_ALTERNATIVES
    if analysis_years is None:
        analysis_years = mortgage.remaining_years

    # Baseline: no extra payments
    baseline = simulate_mortgage(mortgage, 0)
    baseline_total_interest = sum(m["interest"] for m in baseline)
    baseline_months = len(baseline)

    results = {
        "mortgage": mortgage,
        "baseline_total_interest": baseline_total_interest,
        "baseline_months": baseline_months,
        "baseline_total_cost": sum(m["payment"] for m in baseline),
        "scenarios": [],
    }

    effective_rate = mortgage.annual_interest_rate * (1 - RENTEFRADRAG_RATE)
    results["effective_rate"] = effective_rate
    results["breakeven_returns"] = {}

    for alt in alternatives:
        needed_pretax = effective_rate / (1 - alt.tax_rate)
        results["breakeven_returns"][alt.name] = {
            "pretax_needed": needed_pretax,
            "alt_tax_rate": alt.tax_rate,
            "alt_return": alt.annual_return,
            "beats_mortgage": alt.annual_return * (1 - alt.tax_rate) > effective_rate,
        }

    for extra in extra_amounts:
        scenario = {"extra_monthly": extra}

        sched = simulate_mortgage(mortgage, extra)
        total_interest = sum(m["interest"] for m in sched)
        months_to_payoff = len(sched)

        interest_saved = baseline_total_interest - total_interest
        interest_saved_after_tax = interest_saved * (1 - RENTEFRADRAG_RATE)
        months_saved = baseline_months - months_to_payoff
        total_extra_paid = extra * months_to_payoff

        scenario["total_interest"] = total_interest
        scenario["interest_saved"] = interest_saved
        scenario["interest_saved_after_tax"] = interest_saved_after_tax
        scenario["months_to_payoff"] = months_to_payoff
        scenario["months_saved"] = months_saved
        scenario["years_saved"] = months_saved / 12
        scenario["total_extra_paid"] = total_extra_paid

        # After mortgage is paid off, the freed-up payment can also be invested
        # for the remaining months. This is the "reinvestment" phase.
        freed_monthly = 0
        if months_to_payoff < baseline_months:
            # Average monthly payment during the loan
            avg_payment = sum(m["payment"] for m in baseline) / baseline_months
            freed_monthly = avg_payment + extra  # full payment freed up

        # Compare: wealth at analysis_years with extra payments vs investing
        # Extra payment wealth = interest saved (compounded conceptually) + reinvested freed payments
        analysis_months = analysis_years * 12

        # Mortgage paydown: how much lower is the balance at each year?
        balance_with_extra = []
        balance_baseline = []
        for year in range(1, analysis_years + 1):
            m_idx = min(year * 12 - 1, len(sched) - 1)
            balance_with_extra.append(sched[m_idx]["balance"] if m_idx < len(sched) else 0)
            m_idx_b = min(year * 12 - 1, len(baseline) - 1)
            balance_baseline.append(baseline[m_idx_b]["balance"] if m_idx_b < len(baseline) else 0)

        scenario["balance_by_year"] = balance_with_extra
        scenario["balance_baseline_by_year"] = balance_baseline
        scenario["equity_gain_by_year"] = [
            b - e for b, e in zip(balance_baseline, balance_with_extra)
        ]

        # Net wealth from extra payments = equity gain + interest saved after tax
        # But we need to track cumulative interest saved per year
        cumulative_interest_saved = []
        cum_base = 0
        cum_extra = 0
        for year in range(1, analysis_years + 1):
            for m in range(12):
                idx = (year - 1) * 12 + m
                if idx < len(baseline):
                    cum_base += baseline[idx]["interest"]
                if idx < len(sched):
                    cum_extra += sched[idx]["interest"]
            cumulative_interest_saved.append(
                (cum_base - cum_extra) * (1 - RENTEFRADRAG_RATE)
            )

        scenario["cumulative_interest_saved_after_tax"] = cumulative_interest_saved

        # Total mortgage paydown wealth = extra equity + cumulative interest savings
        scenario["mortgage_paydown_wealth"] = [
            eq + isv for eq, isv in zip(
                scenario["equity_gain_by_year"],
                cumulative_interest_saved,
            )
        ]

        # Alternative: invest the extra monthly in each alternative
        scenario["alternatives"] = {}
        for alt in alternatives:
            inv_sched = simulate_investment(
                extra, alt.annual_return, analysis_years, alt.tax_rate
            )
            scenario["alternatives"][alt.name] = {
                "schedule": inv_sched,
                "net_at_end": inv_sched[-1]["net_after_tax"] if inv_sched else 0,
                "alt_return": alt.annual_return,
                "alt_tax_rate": alt.tax_rate,
            }

        results["scenarios"].append(scenario)

    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def format_nok(amount):
    if amount < 0:
        return f"-{abs(amount):,.0f} kr".replace(",", " ")
    return f"{amount:,.0f} kr".replace(",", " ")


def print_analysis(results, milestones=None):
    """Print comprehensive analysis report."""
    m = results["mortgage"]
    if milestones is None:
        milestones = [5, 10, 15, 20, m.remaining_years]
        milestones = sorted(set(y for y in milestones if y <= m.remaining_years))

    w = 100
    print()
    print("=" * w)
    print("  EXTRA MORTGAGE PAYMENTS vs ALTERNATIVE INVESTMENTS".center(w))
    print("=" * w)

    print(f"\n  Mortgage details:")
    print(f"    Remaining balance:    {format_nok(m.remaining_balance):>20s}")
    print(f"    Interest rate:        {m.annual_interest_rate*100:>19.2f}%")
    print(f"    Remaining term:       {m.remaining_years:>17d} years")
    print(f"    Loan type:            {m.loan_type:>20s}")

    print(f"\n  Tax-adjusted rates:")
    print(f"    Nominal rate:         {m.annual_interest_rate*100:>19.2f}%")
    print(f"    After rentefradrag:   {results['effective_rate']*100:>19.2f}%  (rate × {1-RENTEFRADRAG_RATE})")
    print(f"    This is your hurdle — alternatives must beat {results['effective_rate']*100:.2f}% after tax")

    baseline_months = results["baseline_months"]
    baseline_interest = results["baseline_total_interest"]

    print(f"\n  Baseline (no extra payments):")
    print(f"    Payoff in:            {baseline_months:>14d} months ({baseline_months/12:.1f} years)")
    print(f"    Total interest:       {format_nok(baseline_interest):>20s}")
    print(f"    After rentefradrag:   {format_nok(baseline_interest * (1 - RENTEFRADRAG_RATE)):>20s}")

    # --- Break-even returns ---
    print(f"\n\n  {'BREAK-EVEN RETURNS':^{w}}")
    print("  " + "-" * (w - 4))
    print(f"  What annual return does each alternative need to beat paying down the mortgage?\n")
    print(f"  {'Alternative':<35s} {'Tax rate':>10s} {'Need pre-tax':>14s} {'Actual return':>14s} {'Verdict':>12s}")
    print("  " + "-" * (w - 4))

    for name, info in results["breakeven_returns"].items():
        verdict = "INVEST" if info["beats_mortgage"] else "PAY LOAN"
        marker = " ←" if info["beats_mortgage"] else ""
        print(f"  {name:<35s} {info['alt_tax_rate']*100:>9.1f}% {info['pretax_needed']*100:>13.2f}% "
              f"{info['alt_return']*100:>13.1f}% {verdict:>12s}{marker}")

    # --- Per-scenario analysis ---
    for sc in results["scenarios"]:
        extra = sc["extra_monthly"]
        print(f"\n\n  {'─' * (w-4)}")
        print(f"  EXTRA PAYMENT: {format_nok(extra)}/month")
        print(f"  {'─' * (w-4)}")

        print(f"\n  Mortgage impact:")
        print(f"    Months to payoff:     {sc['months_to_payoff']:>14d}  (was {baseline_months})")
        print(f"    Time saved:           {sc['months_saved']:>11d} mo  ({sc['years_saved']:.1f} years)")
        print(f"    Interest saved:       {format_nok(sc['interest_saved']):>20s}")
        print(f"    After rentefradrag:   {format_nok(sc['interest_saved_after_tax']):>20s}")
        print(f"    Total extra paid:     {format_nok(sc['total_extra_paid']):>20s}")
        roi = sc['interest_saved_after_tax'] / sc['total_extra_paid'] * 100 if sc['total_extra_paid'] > 0 else 0
        print(f"    Return on extra:      {roi:>19.1f}%  (interest saved / extra paid)")

        # Wealth comparison table
        print(f"\n  Net wealth gain at each milestone:")
        header = f"  {'Year':<6s} {'Mortgage paydown':>18s}"
        alt_names = list(sc["alternatives"].keys())
        for an in alt_names:
            short = an[:20]
            header += f" {short:>22s}"
        header += f" {'Best choice':>14s}"
        print(header)
        print("  " + "-" * (len(header) - 2))

        for y in milestones:
            if y > len(sc["mortgage_paydown_wealth"]):
                continue
            mort_w = sc["mortgage_paydown_wealth"][y - 1]
            line = f"  {y:<6d} {format_nok(mort_w):>18s}"

            alt_values = {}
            for an in alt_names:
                alt_data = sc["alternatives"][an]
                if y <= len(alt_data["schedule"]):
                    alt_w = alt_data["schedule"][y - 1]["net_after_tax"]
                else:
                    alt_w = alt_data["net_at_end"]
                alt_values[an] = alt_w
                short = an[:20]
                line += f" {format_nok(alt_w):>22s}"

            all_options = {"Mortgage": mort_w}
            all_options.update(alt_values)
            best = max(all_options, key=all_options.get)
            best_short = best[:14]
            line += f" {best_short:>14s}"
            print(line)

    # --- Sensitivity table ---
    print(f"\n\n  {'SENSITIVITY: Interest saved after tax by extra payment amount and rate':^{w}}")
    print("  " + "-" * (w - 4))

    rates = [0.03, 0.04, 0.05, 0.055, 0.06, 0.07]
    extras = [1000, 2000, 3000, 5000, 10000]

    header = f"  {'Extra/mo':<12s}"
    for r in rates:
        header += f" {'Rate '+f'{r*100:.1f}%':>12s}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for extra in extras:
        line = f"  {format_nok(extra):<12s}"
        for r in rates:
            temp_m = MortgageDetails(
                remaining_balance=m.remaining_balance,
                annual_interest_rate=r,
                remaining_years=m.remaining_years,
                loan_type=m.loan_type,
            )
            base = simulate_mortgage(temp_m, 0)
            with_extra = simulate_mortgage(temp_m, extra)
            saved = sum(b["interest"] for b in base) - sum(e["interest"] for e in with_extra)
            saved_after_tax = saved * (1 - RENTEFRADRAG_RATE)
            line += f" {format_nok(saved_after_tax):>12s}"
        print(line)

    print(f"\n  (Interest saved over full loan term, after 22% rentefradrag)")

    # --- Summary ---
    print(f"\n\n{'=' * w}")
    print("  SUMMARY".center(w))
    print("=" * w)

    eff = results["effective_rate"]
    print(f"""
  Your effective mortgage cost after rentefradrag: {eff*100:.2f}%

  RULE OF THUMB:
  • If you can earn > {eff*100:.1f}% after tax elsewhere → invest
  • If not → pay down the mortgage

  In practice with Norwegian tax rates:
  • Global index fund at 7% → after {STOCK_GAIN_TAX_RATE*100:.1f}% tax = {7*(1-STOCK_GAIN_TAX_RATE):.2f}%
    → {'BEATS' if 0.07*(1-STOCK_GAIN_TAX_RATE) > eff else 'LOSES to'} mortgage at {m.annual_interest_rate*100:.1f}%
  • Savings account at 3.5% → after {CAPITAL_INCOME_TAX_RATE*100:.0f}% tax = {3.5*(1-CAPITAL_INCOME_TAX_RATE):.2f}%
    → {'BEATS' if 0.035*(1-CAPITAL_INCOME_TAX_RATE) > eff else 'LOSES to'} mortgage at {m.annual_interest_rate*100:.1f}%

  FACTORS BEYOND PURE RETURN:
  • Mortgage paydown is RISK-FREE (guaranteed {eff*100:.2f}% return)
  • Stocks average higher but can drop 30-50% in any given year
  • Liquidity: extra mortgage payments are locked in; investments are accessible
  • Behavioral: forced paydown builds discipline; investments can be raided
  • Opportunity cost: lower mortgage = lower required income = more flexibility
""")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def generate_charts(results, output_dir="output"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import numpy as np
    import os

    os.makedirs(output_dir, exist_ok=True)

    BLUE = "#2196F3"
    ORANGE = "#FF7043"
    GREEN = "#66BB6A"
    RED = "#EF5350"
    PURPLE = "#AB47BC"
    COLORS = [BLUE, GREEN, ORANGE, PURPLE, RED, "#78909C", "#FFA726"]
    plt.style.use("seaborn-v0_8-whitegrid")

    def nok_fmt(x, _):
        if abs(x) >= 1_000_000:
            return f"{x/1e6:.1f}M"
        if abs(x) >= 1_000:
            return f"{x/1e3:.0f}k"
        return f"{x:.0f}"

    m = results["mortgage"]
    years = m.remaining_years
    x_years = list(range(1, years + 1))

    # Chart 1: Wealth comparison – mortgage paydown vs alternatives
    for sc in results["scenarios"]:
        extra = sc["extra_monthly"]
        fig, ax = plt.subplots(figsize=(14, 7))

        # Mortgage paydown wealth
        mort_wealth = sc["mortgage_paydown_wealth"][:years]
        ax.plot(x_years[:len(mort_wealth)], mort_wealth, "-", color=BLUE,
                linewidth=2.5, label=f"Mortgage paydown ({format_nok(extra)}/mo)")

        # Alternatives
        for i, (alt_name, alt_data) in enumerate(sc["alternatives"].items()):
            sched = alt_data["schedule"]
            alt_wealth = [s["net_after_tax"] for s in sched][:years]
            color = COLORS[(i + 1) % len(COLORS)]
            ax.plot(range(1, len(alt_wealth) + 1), alt_wealth, "-", color=color,
                    linewidth=1.5, label=f"{alt_name} ({alt_data['alt_return']*100:.0f}%)")

        ax.axhline(y=0, color="black", linewidth=0.5)
        ax.set_xlabel("Years", fontsize=12)
        ax.set_ylabel("Net Wealth Gain (NOK)", fontsize=12)
        ax.set_title(f"Extra {format_nok(extra)}/mo: Mortgage Paydown vs Alternative Investments\n"
                     f"Mortgage: {format_nok(m.remaining_balance)} @ {m.annual_interest_rate*100:.1f}%, "
                     f"{m.remaining_years} years remaining", fontsize=13)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
        ax.legend(loc="upper left", fontsize=9)
        plt.tight_layout()

        fname = f"{output_dir}/extra_payments_{int(extra)}.png"
        plt.savefig(fname, dpi=150)
        plt.close()
        print(f"Saved: {fname}")

    # Chart 2: Break-even visualization
    fig, ax = plt.subplots(figsize=(14, 6))
    eff_rate = results["effective_rate"]

    alt_names = []
    alt_returns_after_tax = []
    bar_colors = []
    for name, info in results["breakeven_returns"].items():
        alt_names.append(name)
        after_tax = info["alt_return"] * (1 - info["alt_tax_rate"])
        alt_returns_after_tax.append(after_tax * 100)
        bar_colors.append(GREEN if info["beats_mortgage"] else RED)

    x = np.arange(len(alt_names))
    bars = ax.bar(x, alt_returns_after_tax, color=bar_colors, alpha=0.8, edgecolor="white")
    ax.axhline(y=eff_rate * 100, color=BLUE, linewidth=2.5, linestyle="--",
               label=f"Mortgage effective cost: {eff_rate*100:.2f}%")

    ax.set_xticks(x)
    ax.set_xticklabels(alt_names, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("After-tax return (%)", fontsize=12)
    ax.set_title(f"Break-Even: Alternative Returns vs Effective Mortgage Cost\n"
                 f"Green = beats mortgage, Red = mortgage wins", fontsize=13)
    ax.legend(fontsize=11)

    for i, v in enumerate(alt_returns_after_tax):
        ax.text(i, v + 0.15, f"{v:.2f}%", ha="center", fontsize=9, fontweight="bold")

    plt.tight_layout()
    plt.savefig(f"{output_dir}/breakeven_analysis.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir}/breakeven_analysis.png")

    # Chart 3: Balance trajectory with different extra payment levels
    fig, ax = plt.subplots(figsize=(14, 6))

    extras_to_plot = [0] + [sc["extra_monthly"] for sc in results["scenarios"]]
    for i, extra in enumerate(extras_to_plot):
        sched = simulate_mortgage(m, extra)
        months = [s["month"] for s in sched]
        balances = [s["balance"] for s in sched]
        color = COLORS[i % len(COLORS)]
        label = "No extra" if extra == 0 else f"+{format_nok(extra)}/mo"
        ax.plot([m/12 for m in months], balances, "-", color=color, linewidth=1.8, label=label)

    ax.set_xlabel("Years", fontsize=12)
    ax.set_ylabel("Remaining Balance (NOK)", fontsize=12)
    ax.set_title("Mortgage Balance Over Time with Extra Payments", fontsize=14)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(nok_fmt))
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/balance_trajectories.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir}/balance_trajectories.png")

    # Chart 4: Sensitivity heatmap – interest saved by rate and extra amount
    fig, ax = plt.subplots(figsize=(12, 6))
    rates = [0.03, 0.04, 0.05, 0.055, 0.06, 0.07]
    extras = [1000, 2000, 3000, 5000, 7500, 10000]

    data = np.zeros((len(extras), len(rates)))
    for i, extra in enumerate(extras):
        for j, rate in enumerate(rates):
            temp_m = MortgageDetails(m.remaining_balance, rate, m.remaining_years, m.loan_type)
            base = simulate_mortgage(temp_m, 0)
            with_extra = simulate_mortgage(temp_m, extra)
            saved = sum(b["interest"] for b in base) - sum(e["interest"] for e in with_extra)
            data[i, j] = saved * (1 - RENTEFRADRAG_RATE)

    im = ax.imshow(data / 1000, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(rates)))
    ax.set_xticklabels([f"{r*100:.1f}%" for r in rates])
    ax.set_yticks(range(len(extras)))
    ax.set_yticklabels([f"{e:,.0f} kr" for e in extras])
    ax.set_xlabel("Interest Rate", fontsize=12)
    ax.set_ylabel("Extra Payment / Month", fontsize=12)
    ax.set_title("Interest Saved (thousands NOK, after tax) by Rate & Extra Payment", fontsize=13)

    for i in range(len(extras)):
        for j in range(len(rates)):
            ax.text(j, i, f"{data[i,j]/1000:.0f}k", ha="center", va="center", fontsize=9,
                    color="white" if data[i,j] > data.max()*0.6 else "black")

    fig.colorbar(im, ax=ax, label="Interest saved (thousands NOK)")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/sensitivity_heatmap.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir}/sensitivity_heatmap.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: typical Norwegian mortgage
    mortgage = MortgageDetails(
        remaining_balance=3_500_000,
        annual_interest_rate=0.05,
        remaining_years=20,
        loan_type="annuity",
    )

    extra_amounts = [2_000, 5_000, 10_000]

    results = analyze_extra_payments(
        mortgage,
        extra_amounts,
        alternatives=DEFAULT_ALTERNATIVES,
    )

    print_analysis(results)
    generate_charts(results)
    print("\nAll charts saved to output/")
