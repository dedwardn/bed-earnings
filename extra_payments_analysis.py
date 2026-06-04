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

Investment return assumptions are grounded in historical rolling-window
data from major indices (see HISTORICAL_RETURNS below).
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


# ---------------------------------------------------------------------------
# Historical rolling-window return data
# ---------------------------------------------------------------------------
# Sources: S&P 500 (1926-2024), MSCI World (1970-2024), Bloomberg Agg (1990-2024)
# All figures are annualized nominal total returns in USD.
# Norwegian investors face additional currency risk; NOK has historically
# depreciated vs USD, making USD-denominated returns slightly higher in NOK
# terms over long periods.

HISTORICAL_RETURNS = {
    "sp500": {
        "description": "S&P 500 Total Return (USD, nominal)",
        "source": "1926–2024, ~89 rolling 10-year windows",
        "rolling_10yr": {
            "worst": -0.015,      # Starting 1999 (dot-com + GFC)
            "p25": 0.065,
            "median": 0.100,
            "p75": 0.135,
            "best": 0.201,        # Starting 1949
        },
        "rolling_20yr": {
            "worst": 0.031,       # No negative 20-year window
            "median": 0.107,
            "best": 0.178,
        },
    },
    "msci_world": {
        "description": "MSCI World Index (USD, net total return)",
        "source": "1970–2024, ~45 rolling 10-year windows",
        "rolling_10yr": {
            "worst": 0.002,       # 2000–2009 (dot-com + GFC)
            "p25": 0.055,
            "median": 0.0808,
            "p75": 0.110,
            "best": 0.155,
        },
        "rolling_20yr": {
            "worst": 0.025,
            "median": 0.085,
            "best": 0.130,
        },
        "long_term_avg": 0.0888,  # 1986–2025
    },
    "global_bonds": {
        "description": "Bloomberg Global Aggregate Bond Index",
        "source": "1990–2024",
        "rolling_10yr": {
            "worst": -0.02,       # 2013–2023 (rate hike cycle)
            "p25": 0.025,
            "median": 0.048,
            "p75": 0.065,
            "best": 0.09,
        },
        "long_term_avg": 0.048,
    },
    "oslo_bors": {
        "description": "Oslo Børs (OSEBX)",
        "source": "1997–2021 (World Bank / TheGlobalEconomy)",
        "arithmetic_mean": 0.1202,
    },
    "norwegian_inflation": {
        "avg_25yr": 0.0244,       # 2000–2024
        "avg_20yr": 0.021,        # 2000–2019 (pre-spike)
        "recent_decade_avg": 0.0295,  # 2015–2024
    },
}


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
    historical_basis: str = ""     # Which historical figure this is based on


# ---------------------------------------------------------------------------
# Default alternatives – grounded in historical rolling 10-year medians
# ---------------------------------------------------------------------------
DEFAULT_ALTERNATIVES = [
    AlternativeInvestment(
        "Global index fund (ASK)",
        HISTORICAL_RETURNS["msci_world"]["rolling_10yr"]["median"],  # 8.08%
        STOCK_GAIN_TAX_RATE, "medium",
        "MSCI World rolling 10yr median",
    ),
    AlternativeInvestment(
        "Norwegian/US equity (ASK)",
        HISTORICAL_RETURNS["sp500"]["rolling_10yr"]["median"],  # 10.0%
        STOCK_GAIN_TAX_RATE, "high",
        "S&P 500 rolling 10yr median",
    ),
    AlternativeInvestment(
        "Bond fund",
        HISTORICAL_RETURNS["global_bonds"]["long_term_avg"],  # 4.8%
        CAPITAL_INCOME_TAX_RATE, "low",
        "Bloomberg Global Agg 30yr avg",
    ),
    AlternativeInvestment(
        "High-yield savings",
        0.035,
        CAPITAL_INCOME_TAX_RATE, "low",
        "Current Norwegian market rate",
    ),
]

# Conservative scenario: 25th percentile rolling 10yr returns
CONSERVATIVE_ALTERNATIVES = [
    AlternativeInvestment(
        "Global index (conservative)",
        HISTORICAL_RETURNS["msci_world"]["rolling_10yr"]["p25"],  # 5.5%
        STOCK_GAIN_TAX_RATE, "medium",
        "MSCI World rolling 10yr 25th pctl",
    ),
    AlternativeInvestment(
        "US equity (conservative)",
        HISTORICAL_RETURNS["sp500"]["rolling_10yr"]["p25"],  # 6.5%
        STOCK_GAIN_TAX_RATE, "high",
        "S&P 500 rolling 10yr 25th pctl",
    ),
    AlternativeInvestment(
        "Bond fund (conservative)",
        HISTORICAL_RETURNS["global_bonds"]["rolling_10yr"]["worst"],  # -2%
        CAPITAL_INCOME_TAX_RATE, "low",
        "Bloomberg Global Agg rolling 10yr worst",
    ),
]

# Optimistic scenario: 75th percentile rolling 10yr returns
OPTIMISTIC_ALTERNATIVES = [
    AlternativeInvestment(
        "Global index (optimistic)",
        HISTORICAL_RETURNS["msci_world"]["rolling_10yr"]["p75"],  # 11.0%
        STOCK_GAIN_TAX_RATE, "medium",
        "MSCI World rolling 10yr 75th pctl",
    ),
    AlternativeInvestment(
        "US equity (optimistic)",
        HISTORICAL_RETURNS["sp500"]["rolling_10yr"]["p75"],  # 13.5%
        STOCK_GAIN_TAX_RATE, "high",
        "S&P 500 rolling 10yr 75th pctl",
    ),
    AlternativeInvestment(
        "Bond fund (optimistic)",
        HISTORICAL_RETURNS["global_bonds"]["rolling_10yr"]["best"],  # 9.0%
        CAPITAL_INCOME_TAX_RATE, "low",
        "Bloomberg Global Agg rolling 10yr best",
    ),
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


def simulate_committed_budget(
    mortgage: MortgageDetails,
    extra: float,
    invest_return: float,
    invest_tax: float,
    horizon_years: int,
    strategy: str = "amortize",
    rentefradrag: float = RENTEFRADRAG_RATE,
):
    """
    Equal-budget net-worth simulation for three mortgage strategies.

    Every month the same total budget is committed: the normal mortgage
    payment (interest + scheduled principal of an amortizing loan) PLUS `extra`.
    Mortgage interest is charged at its AFTER-TAX cost — interest × (1 − 0.22) —
    because the 22% rentefradrag is cash you get back, so it stays available to
    invest. Whatever the strategy does not spend on the mortgage is invested at
    `invest_return`.

    Strategies (all share the identical out-of-pocket budget):
      • "prepay"        – throw base payment + extra at the mortgage; only the
                          tax refund is invested until it is repaid, then the
                          whole freed-up budget flows into investments.
      • "amortize"      – pay the normal amortizing payment, invest `extra`
                          (plus the tax refund, and the freed base once it ends).
      • "interest_only" – pay ONLY the interest, never reduce principal; invest
                          the scheduled-principal portion + extra every month.
                          The full balance stays outstanding the whole horizon,
                          keeping the maximum interest deduction.

    Compared on net worth = (investment value after exit tax) − (remaining
    mortgage balance). Returns net worth by year-end (length horizon_years).
    """
    mr = mortgage.annual_interest_rate / 12
    total_months = mortgage.remaining_years * 12

    if mortgage.loan_type == "annuity":
        base_payment = calculate_annuity_payment(
            mortgage.remaining_balance, mortgage.annual_interest_rate, total_months
        )
    else:
        base_payment = mortgage.remaining_balance / total_months + mortgage.remaining_balance * mr

    monthly_budget = base_payment + extra
    invest_mr = (1 + invest_return) ** (1 / 12) - 1

    balance = mortgage.remaining_balance
    fund = 0.0
    invested = 0.0
    networth_by_year = []

    for month in range(1, horizon_years * 12 + 1):
        if balance > 0.01:
            interest = balance * mr
            if strategy == "interest_only":
                principal = 0.0
            else:
                if mortgage.loan_type == "annuity":
                    sched_principal = base_payment - interest
                else:
                    sched_principal = mortgage.remaining_balance / total_months
                prepay = extra if strategy == "prepay" else 0.0
                principal = min(sched_principal + prepay, balance)
            balance = max(0.0, balance - principal)
            # After-tax interest cost; the 22% refund stays investable
            effective_outlay = interest * (1 - rentefradrag) + principal
        else:
            effective_outlay = 0.0

        leftover = max(0.0, monthly_budget - effective_outlay)
        fund = fund * (1 + invest_mr) + leftover
        invested += leftover

        if month % 12 == 0:
            gain = fund - invested
            tax = max(0.0, gain * invest_tax)
            networth_by_year.append((fund - tax) - balance)

    return networth_by_year


def analyze_extra_payments(
    mortgage: MortgageDetails,
    extra_amounts: list[float],
    alternatives: Optional[list[AlternativeInvestment]] = None,
    analysis_years: Optional[int] = None,
    reinvest_return: float = 0.035,
    reinvest_tax: float = CAPITAL_INCOME_TAX_RATE,
):
    """
    Full analysis comparing extra mortgage payments vs alternative investments.

    `reinvest_return`/`reinvest_tax` set what the prepay strategy does with the
    cashflow freed up once the mortgage is paid off early. Default is the
    risk-free high-yield savings rate (3.5%), so the "Mortgage paydown" line
    represents the conservative, guaranteed strategy: prepay aggressively, then
    park the freed payments safely.

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
    results["reinvest_return"] = reinvest_return
    results["reinvest_tax"] = reinvest_tax
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

        # --- Mortgage paydown wealth (equal-budget net-worth model) ---
        # Prepay all `extra` into the mortgage, then invest the freed cashflow
        # at the (conservative) reinvest rate once the loan is gone. Net worth
        # is measured as a GAIN vs doing nothing with the extra, so we add back
        # the baseline balance: gain = (fund − prepay_balance) + baseline_balance
        #                            = fund + equity_gain.
        # This captures BOTH the interest saved and the reinvested freed cash,
        # and never collapses the way the old equity-gap formula did.
        prepay_networth = simulate_committed_budget(
            mortgage, extra, reinvest_return, reinvest_tax,
            analysis_years, strategy="prepay",
        )
        scenario["mortgage_paydown_wealth"] = [
            nw + bb for nw, bb in zip(prepay_networth, balance_baseline)
        ]

        # --- Alternatives: amortize normally, invest the extra in each fund ---
        # (base → mortgage on schedule, extra + tax refund → fund; after the
        #  baseline loan is paid off the freed base is invested too).
        scenario["alternatives"] = {}
        for alt in alternatives:
            alt_networth = simulate_committed_budget(
                mortgage, extra, alt.annual_return, alt.tax_rate,
                analysis_years, strategy="amortize",
            )
            wealth_by_year = [nw + bb for nw, bb in zip(alt_networth, balance_baseline)]
            scenario["alternatives"][alt.name] = {
                "wealth_by_year": wealth_by_year,
                "net_at_end": wealth_by_year[-1] if wealth_by_year else 0,
                "alt_return": alt.annual_return,
                "alt_tax_rate": alt.tax_rate,
            }

        # --- Interest-only (maximum leverage): pay only interest, invest the
        #     scheduled principal + extra in each fund. The full balance stays
        #     outstanding the whole horizon (subtracted from net worth). ---
        scenario["interest_only"] = {}
        for alt in alternatives:
            io_networth = simulate_committed_budget(
                mortgage, extra, alt.annual_return, alt.tax_rate,
                analysis_years, strategy="interest_only",
            )
            io_wealth = [nw + bb for nw, bb in zip(io_networth, balance_baseline)]
            scenario["interest_only"][alt.name] = {
                "wealth_by_year": io_wealth,
                "net_at_end": io_wealth[-1] if io_wealth else 0,
                "alt_return": alt.annual_return,
                "alt_tax_rate": alt.tax_rate,
            }

        results["scenarios"].append(scenario)

    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _estimate_pct_beating_hurdle(rolling_10yr: dict, hurdle: float) -> float:
    """
    Estimate what percentage of historical rolling 10yr windows beat a hurdle rate.
    Uses linear interpolation between known percentile points.
    """
    points = [
        (0.0, rolling_10yr["worst"]),
        (0.25, rolling_10yr["p25"]),
        (0.50, rolling_10yr["median"]),
        (0.75, rolling_10yr["p75"]),
        (1.0, rolling_10yr["best"]),
    ]
    if hurdle <= points[0][1]:
        return 100.0
    if hurdle >= points[-1][1]:
        return 0.0
    for i in range(len(points) - 1):
        pct_lo, ret_lo = points[i]
        pct_hi, ret_hi = points[i + 1]
        if ret_lo <= hurdle <= ret_hi:
            frac = (hurdle - ret_lo) / (ret_hi - ret_lo)
            pct_at_hurdle = pct_lo + frac * (pct_hi - pct_lo)
            return (1.0 - pct_at_hurdle) * 100
    return 50.0


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
                if y <= len(alt_data["wealth_by_year"]):
                    alt_w = alt_data["wealth_by_year"][y - 1]
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

        # --- Three leverage strategies (for the first equity fund) ---
        if sc.get("interest_only"):
            ref = next((n for n in alt_names if "ndex" in n or "quity" in n), alt_names[0])
            print(f"\n  Three leverage strategies (investing in {ref}):")
            print(f"    {'Year':<6s} {'Prepay (max paydown)':>22s} {'Amortize + invest':>22s} {'Interest-only (max lev.)':>26s}")
            print("    " + "-" * 78)
            for y in milestones:
                if y > len(sc["mortgage_paydown_wealth"]):
                    continue
                pp = sc["mortgage_paydown_wealth"][y - 1]
                am = sc["alternatives"][ref]["wealth_by_year"][y - 1]
                io = sc["interest_only"][ref]["wealth_by_year"][y - 1]
                print(f"    {y:<6d} {format_nok(pp):>22s} {format_nok(am):>22s} {format_nok(io):>26s}")
            print(f"    (Interest-only keeps the full balance outstanding — amplifies BOTH gains and losses)")

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

    # --- Historical context ---
    print(f"\n\n  {'HISTORICAL ROLLING-WINDOW CONTEXT':^{w}}")
    print("  " + "-" * (w - 4))
    print(f"  Return assumptions grounded in actual historical data:\n")

    for key, label, tax in [
        ("msci_world", "MSCI World (global index)", STOCK_GAIN_TAX_RATE),
        ("sp500", "S&P 500 (US equity)", STOCK_GAIN_TAX_RATE),
        ("global_bonds", "Global bonds", CAPITAL_INCOME_TAX_RATE),
    ]:
        data = HISTORICAL_RETURNS[key]
        r10 = data["rolling_10yr"]
        print(f"  {label} — {data['source']}")
        print(f"    Rolling 10yr:  worst {r10['worst']*100:+.1f}%  |  median {r10['median']*100:.1f}%"
              f"  |  best {r10['best']*100:.1f}%")
        if "rolling_20yr" in data:
            r20 = data["rolling_20yr"]
            print(f"    Rolling 20yr:  worst {r20['worst']*100:+.1f}%  |  median {r20['median']*100:.1f}%"
                  f"  |  best {r20['best']*100:.1f}%")

        eff = results["effective_rate"]
        needed_pretax = eff / (1 - tax)
        pct_beating = _estimate_pct_beating_hurdle(r10, needed_pretax)
        print(f"    → Need {needed_pretax*100:.2f}% pre-tax to beat mortgage"
              f" → ~{pct_beating:.0f}% of historical 10yr windows beat this")
        print()

    print(f"  Norwegian inflation: 25yr avg {HISTORICAL_RETURNS['norwegian_inflation']['avg_25yr']*100:.1f}%,"
          f" recent decade {HISTORICAL_RETURNS['norwegian_inflation']['recent_decade_avg']*100:.1f}%"
          f" (2022–23 spike pulls recent average up)")

    # --- Summary ---
    print(f"\n\n{'=' * w}")
    print("  SUMMARY".center(w))
    print("=" * w)

    eff = results["effective_rate"]
    msci_med = HISTORICAL_RETURNS["msci_world"]["rolling_10yr"]["median"]
    msci_after = msci_med * (1 - STOCK_GAIN_TAX_RATE)
    savings_rate = 0.035
    savings_after = savings_rate * (1 - CAPITAL_INCOME_TAX_RATE)
    print(f"""
  Your effective mortgage cost after rentefradrag: {eff*100:.2f}%

  RULE OF THUMB:
  • If you can earn > {eff*100:.1f}% after tax elsewhere → invest
  • If not → pay down the mortgage

  HISTORICAL VERDICT (at your mortgage rate of {m.annual_interest_rate*100:.1f}%):
  • Global index fund (MSCI World median {msci_med*100:.1f}%) → after {STOCK_GAIN_TAX_RATE*100:.1f}% tax = {msci_after*100:.2f}%
    → {'BEATS' if msci_after > eff else 'LOSES to'} mortgage — and has done so in ~{_estimate_pct_beating_hurdle(HISTORICAL_RETURNS["msci_world"]["rolling_10yr"], eff / (1 - STOCK_GAIN_TAX_RATE)):.0f}% of rolling 10yr windows
  • Savings account at {savings_rate*100:.1f}% → after {CAPITAL_INCOME_TAX_RATE*100:.0f}% tax = {savings_after*100:.2f}%
    → {'BEATS' if savings_after > eff else 'LOSES to'} mortgage at {m.annual_interest_rate*100:.1f}%

  20-YEAR PERSPECTIVE:
  • No 20-year rolling window for S&P 500 has returned below {HISTORICAL_RETURNS["sp500"]["rolling_20yr"]["worst"]*100:.1f}%
  • MSCI World 20yr worst: {HISTORICAL_RETURNS["msci_world"]["rolling_20yr"]["worst"]*100:.1f}% — still marginal vs mortgage
  • Longer horizons strongly favor equities, but past performance ≠ guaranteed future

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
            alt_wealth = alt_data["wealth_by_year"][:years]
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
    mortgage = MortgageDetails(
        remaining_balance=3_500_000,
        annual_interest_rate=0.05,
        remaining_years=20,
        loan_type="annuity",
    )

    extra_amounts = [2_000, 5_000, 10_000]

    # Main analysis with median historical returns
    results = analyze_extra_payments(
        mortgage,
        extra_amounts,
        alternatives=DEFAULT_ALTERNATIVES,
    )
    print_analysis(results)
    generate_charts(results)

    # Conservative scenario (25th percentile returns)
    print("\n" + "=" * 100)
    print("  CONSERVATIVE SCENARIO (25th percentile rolling 10yr returns)".center(100))
    print("=" * 100)
    conservative_results = analyze_extra_payments(
        mortgage, [5_000], alternatives=CONSERVATIVE_ALTERNATIVES,
    )
    for sc in conservative_results["scenarios"]:
        extra = sc["extra_monthly"]
        print(f"\n  Extra {format_nok(extra)}/mo — conservative market returns:")
        mort_w = sc["mortgage_paydown_wealth"][-1]
        print(f"    Mortgage paydown wealth at year {mortgage.remaining_years}: {format_nok(mort_w)}")
        for alt_name, alt_data in sc["alternatives"].items():
            print(f"    {alt_name} ({alt_data['alt_return']*100:.1f}%): {format_nok(alt_data['net_at_end'])}")

    # Optimistic scenario (75th percentile returns)
    print("\n" + "=" * 100)
    print("  OPTIMISTIC SCENARIO (75th percentile rolling 10yr returns)".center(100))
    print("=" * 100)
    optimistic_results = analyze_extra_payments(
        mortgage, [5_000], alternatives=OPTIMISTIC_ALTERNATIVES,
    )
    for sc in optimistic_results["scenarios"]:
        extra = sc["extra_monthly"]
        print(f"\n  Extra {format_nok(extra)}/mo — optimistic market returns:")
        mort_w = sc["mortgage_paydown_wealth"][-1]
        print(f"    Mortgage paydown wealth at year {mortgage.remaining_years}: {format_nok(mort_w)}")
        for alt_name, alt_data in sc["alternatives"].items():
            print(f"    {alt_name} ({alt_data['alt_return']*100:.1f}%): {format_nok(alt_data['net_at_end'])}")

    print("\n\nAll charts saved to output/")
