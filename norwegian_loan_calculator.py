"""
Norwegian Loan Calculator
=========================

Compares annuity and serial (linear) loans with Norwegian tax law considerations:
- 22% tax deduction on interest payments (rentefradrag)
- Rental income taxation (utleieinntekt)
- Short-term vs long-term rental tax rules
- Net cost calculations after tax benefits

Norwegian tax rules applied (2024/2025):
- Interest deduction rate: 22% of interest paid is deducted from tax
- Rental income from part of own home: tax-free if owner uses >= 50%
- Rental income from separate unit / entire property: taxable as capital income (22%)
- Short-term rental (< 30 days): taxable, 85% of gross income above NOK 10,000 threshold
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ---------------------------------------------------------------------------
# Constants – Norwegian tax parameters
# ---------------------------------------------------------------------------
TAX_DEDUCTION_RATE = 0.22          # Rentefradrag – 22% deduction on interest
CAPITAL_INCOME_TAX_RATE = 0.22     # Skatt på kapitalinntekt
SHORT_TERM_RENTAL_THRESHOLD = 10_000  # First NOK 10,000 is tax-free
SHORT_TERM_RENTAL_TAXABLE_SHARE = 0.85  # 85% of income above threshold is taxable


@dataclass
class LoanParameters:
    """Input parameters for a loan calculation."""
    principal: float                # Loan amount in NOK
    annual_interest_rate: float     # Nominal annual interest rate (e.g. 0.05 for 5%)
    term_years: int                 # Loan duration in years
    extra_fees_per_month: float = 0.0   # Termingebyr / monthly admin fee


@dataclass
class RentalParameters:
    """Parameters for rental income calculations."""
    monthly_rental_income: float = 0.0
    is_short_term: bool = False        # < 30 days average stay
    owner_occupies_half: bool = True   # Owner uses >= 50% of the property
    annual_maintenance_cost: float = 0.0  # Deductible costs for taxable rental


@dataclass
class MonthlyPayment:
    """Breakdown of a single monthly payment."""
    month: int
    principal_payment: float
    interest_payment: float
    fee: float
    total_payment: float
    remaining_balance: float
    tax_deduction: float            # Monthly interest * TAX_DEDUCTION_RATE / 12 is
                                    # applied annually, but we track per-month
    net_payment: float              # total_payment - tax_deduction


@dataclass
class AnnualSummary:
    """Summary of payments and tax effects for one year."""
    year: int
    total_principal: float
    total_interest: float
    total_fees: float
    total_payments: float
    tax_deduction: float
    net_cost: float
    remaining_balance: float
    rental_income_gross: float = 0.0
    rental_tax: float = 0.0
    rental_income_net: float = 0.0
    net_cost_after_rental: float = 0.0


@dataclass
class LoanSummary:
    """Full summary of a loan over its entire term."""
    loan_type: str
    principal: float
    annual_interest_rate: float
    term_years: int
    total_paid: float
    total_interest: float
    total_fees: float
    total_tax_deduction: float
    total_net_cost: float
    total_rental_income_gross: float
    total_rental_tax: float
    total_rental_income_net: float
    total_net_cost_after_rental: float
    monthly_payments: list[MonthlyPayment]
    annual_summaries: list[AnnualSummary]


# ---------------------------------------------------------------------------
# Rental income tax helpers
# ---------------------------------------------------------------------------

def calculate_rental_tax(rental: RentalParameters) -> tuple[float, float, float]:
    """
    Calculate annual rental income, tax, and net income.

    Returns:
        (gross_annual, tax, net_annual)
    """
    gross_annual = rental.monthly_rental_income * 12

    if gross_annual == 0:
        return 0.0, 0.0, 0.0

    # Tax-free: owner occupies >= 50% of own home and rents out part of it
    if rental.owner_occupies_half and not rental.is_short_term:
        return gross_annual, 0.0, gross_annual

    if rental.is_short_term:
        # Short-term rental rules
        if gross_annual <= SHORT_TERM_RENTAL_THRESHOLD:
            return gross_annual, 0.0, gross_annual
        taxable = (gross_annual - SHORT_TERM_RENTAL_THRESHOLD) * SHORT_TERM_RENTAL_TAXABLE_SHARE
        tax = taxable * CAPITAL_INCOME_TAX_RATE
        return gross_annual, tax, gross_annual - tax

    # Taxable long-term rental (separate unit or full property)
    taxable = gross_annual - rental.annual_maintenance_cost
    taxable = max(taxable, 0)
    tax = taxable * CAPITAL_INCOME_TAX_RATE
    return gross_annual, tax, gross_annual - tax


# ---------------------------------------------------------------------------
# Serial (linear) loan
# ---------------------------------------------------------------------------

def calculate_serial_loan(
    loan: LoanParameters,
    rental: Optional[RentalParameters] = None,
) -> LoanSummary:
    """
    Calculate a serial (linear) loan schedule.

    In a serial loan the principal repayment is constant each month.
    The interest portion decreases over time as the balance drops.
    """
    n_months = loan.term_years * 12
    monthly_principal = loan.principal / n_months
    monthly_rate = loan.annual_interest_rate / 12
    balance = loan.principal

    monthly_payments: list[MonthlyPayment] = []
    annual_summaries: list[AnnualSummary] = []

    rental_gross, rental_tax, rental_net = calculate_rental_tax(rental) if rental else (0, 0, 0)

    year_principal = year_interest = year_fees = year_total = 0.0

    for m in range(1, n_months + 1):
        interest = balance * monthly_rate
        total = monthly_principal + interest + loan.extra_fees_per_month
        tax_ded = interest * TAX_DEDUCTION_RATE
        net = total - tax_ded

        balance -= monthly_principal
        if balance < 0.01:
            balance = 0.0

        mp = MonthlyPayment(
            month=m,
            principal_payment=round(monthly_principal, 2),
            interest_payment=round(interest, 2),
            fee=round(loan.extra_fees_per_month, 2),
            total_payment=round(total, 2),
            remaining_balance=round(balance, 2),
            tax_deduction=round(tax_ded, 2),
            net_payment=round(net, 2),
        )
        monthly_payments.append(mp)

        year_principal += monthly_principal
        year_interest += interest
        year_fees += loan.extra_fees_per_month
        year_total += total

        if m % 12 == 0:
            year_tax_ded = year_interest * TAX_DEDUCTION_RATE
            net_cost = year_total - year_tax_ded
            annual_summaries.append(AnnualSummary(
                year=m // 12,
                total_principal=round(year_principal, 2),
                total_interest=round(year_interest, 2),
                total_fees=round(year_fees, 2),
                total_payments=round(year_total, 2),
                tax_deduction=round(year_tax_ded, 2),
                net_cost=round(net_cost, 2),
                remaining_balance=round(balance, 2),
                rental_income_gross=round(rental_gross, 2),
                rental_tax=round(rental_tax, 2),
                rental_income_net=round(rental_net, 2),
                net_cost_after_rental=round(net_cost - rental_net, 2),
            ))
            year_principal = year_interest = year_fees = year_total = 0.0

    # Handle remaining months if term doesn't divide evenly by 12
    if n_months % 12 != 0:
        year_tax_ded = year_interest * TAX_DEDUCTION_RATE
        net_cost = year_total - year_tax_ded
        partial_months = n_months % 12
        partial_rental_gross = rental_gross * partial_months / 12
        partial_rental_tax = rental_tax * partial_months / 12
        partial_rental_net = rental_net * partial_months / 12
        annual_summaries.append(AnnualSummary(
            year=n_months // 12 + 1,
            total_principal=round(year_principal, 2),
            total_interest=round(year_interest, 2),
            total_fees=round(year_fees, 2),
            total_payments=round(year_total, 2),
            tax_deduction=round(year_tax_ded, 2),
            net_cost=round(net_cost, 2),
            remaining_balance=0.0,
            rental_income_gross=round(partial_rental_gross, 2),
            rental_tax=round(partial_rental_tax, 2),
            rental_income_net=round(partial_rental_net, 2),
            net_cost_after_rental=round(net_cost - partial_rental_net, 2),
        ))

    totals = _compute_totals("Serial", loan, monthly_payments, annual_summaries)
    return totals


# ---------------------------------------------------------------------------
# Annuity loan
# ---------------------------------------------------------------------------

def calculate_annuity_loan(
    loan: LoanParameters,
    rental: Optional[RentalParameters] = None,
) -> LoanSummary:
    """
    Calculate an annuity loan schedule.

    In an annuity loan the total monthly payment (principal + interest) is
    constant. Early payments are interest-heavy; later payments are
    principal-heavy.
    """
    n_months = loan.term_years * 12
    monthly_rate = loan.annual_interest_rate / 12

    if monthly_rate == 0:
        annuity = loan.principal / n_months
    else:
        annuity = loan.principal * (monthly_rate * (1 + monthly_rate) ** n_months) / \
                  ((1 + monthly_rate) ** n_months - 1)

    balance = loan.principal
    monthly_payments: list[MonthlyPayment] = []
    annual_summaries: list[AnnualSummary] = []

    rental_gross, rental_tax, rental_net = calculate_rental_tax(rental) if rental else (0, 0, 0)

    year_principal = year_interest = year_fees = year_total = 0.0

    for m in range(1, n_months + 1):
        interest = balance * monthly_rate
        principal_payment = annuity - interest
        total = annuity + loan.extra_fees_per_month
        tax_ded = interest * TAX_DEDUCTION_RATE
        net = total - tax_ded

        balance -= principal_payment
        if balance < 0.01:
            balance = 0.0

        mp = MonthlyPayment(
            month=m,
            principal_payment=round(principal_payment, 2),
            interest_payment=round(interest, 2),
            fee=round(loan.extra_fees_per_month, 2),
            total_payment=round(total, 2),
            remaining_balance=round(balance, 2),
            tax_deduction=round(tax_ded, 2),
            net_payment=round(net, 2),
        )
        monthly_payments.append(mp)

        year_principal += principal_payment
        year_interest += interest
        year_fees += loan.extra_fees_per_month
        year_total += total

        if m % 12 == 0:
            year_tax_ded = year_interest * TAX_DEDUCTION_RATE
            net_cost = year_total - year_tax_ded
            annual_summaries.append(AnnualSummary(
                year=m // 12,
                total_principal=round(year_principal, 2),
                total_interest=round(year_interest, 2),
                total_fees=round(year_fees, 2),
                total_payments=round(year_total, 2),
                tax_deduction=round(year_tax_ded, 2),
                net_cost=round(net_cost, 2),
                remaining_balance=round(balance, 2),
                rental_income_gross=round(rental_gross, 2),
                rental_tax=round(rental_tax, 2),
                rental_income_net=round(rental_net, 2),
                net_cost_after_rental=round(net_cost - rental_net, 2),
            ))
            year_principal = year_interest = year_fees = year_total = 0.0

    if n_months % 12 != 0:
        year_tax_ded = year_interest * TAX_DEDUCTION_RATE
        net_cost = year_total - year_tax_ded
        partial_months = n_months % 12
        partial_rental_gross = rental_gross * partial_months / 12
        partial_rental_tax = rental_tax * partial_months / 12
        partial_rental_net = rental_net * partial_months / 12
        annual_summaries.append(AnnualSummary(
            year=n_months // 12 + 1,
            total_principal=round(year_principal, 2),
            total_interest=round(year_interest, 2),
            total_fees=round(year_fees, 2),
            total_payments=round(year_total, 2),
            tax_deduction=round(year_tax_ded, 2),
            net_cost=round(net_cost, 2),
            remaining_balance=0.0,
            rental_income_gross=round(partial_rental_gross, 2),
            rental_tax=round(partial_rental_tax, 2),
            rental_income_net=round(partial_rental_net, 2),
            net_cost_after_rental=round(net_cost - partial_rental_net, 2),
        ))

    totals = _compute_totals("Annuity", loan, monthly_payments, annual_summaries)
    return totals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_totals(
    loan_type: str,
    loan: LoanParameters,
    monthly_payments: list[MonthlyPayment],
    annual_summaries: list[AnnualSummary],
) -> LoanSummary:
    total_paid = sum(mp.total_payment for mp in monthly_payments)
    total_interest = sum(mp.interest_payment for mp in monthly_payments)
    total_fees = sum(mp.fee for mp in monthly_payments)
    total_tax_ded = sum(a.tax_deduction for a in annual_summaries)
    total_net = total_paid - total_tax_ded
    total_rental_gross = sum(a.rental_income_gross for a in annual_summaries)
    total_rental_tax = sum(a.rental_tax for a in annual_summaries)
    total_rental_net = sum(a.rental_income_net for a in annual_summaries)

    return LoanSummary(
        loan_type=loan_type,
        principal=loan.principal,
        annual_interest_rate=loan.annual_interest_rate,
        term_years=loan.term_years,
        total_paid=round(total_paid, 2),
        total_interest=round(total_interest, 2),
        total_fees=round(total_fees, 2),
        total_tax_deduction=round(total_tax_ded, 2),
        total_net_cost=round(total_net, 2),
        total_rental_income_gross=round(total_rental_gross, 2),
        total_rental_tax=round(total_rental_tax, 2),
        total_rental_income_net=round(total_rental_net, 2),
        total_net_cost_after_rental=round(total_net - total_rental_net, 2),
        monthly_payments=monthly_payments,
        annual_summaries=annual_summaries,
    )


# ---------------------------------------------------------------------------
# Comparison & display helpers
# ---------------------------------------------------------------------------

def compare_loans(
    loan: LoanParameters,
    rental: Optional[RentalParameters] = None,
) -> tuple[LoanSummary, LoanSummary]:
    """Calculate both annuity and serial loan and return them for comparison."""
    annuity = calculate_annuity_loan(loan, rental)
    serial = calculate_serial_loan(loan, rental)
    return annuity, serial


def format_nok(amount: float) -> str:
    """Format a number as NOK with space as thousands separator."""
    if amount < 0:
        return f"-{abs(amount):,.0f} kr".replace(",", " ")
    return f"{amount:,.0f} kr".replace(",", " ")


def print_comparison(annuity: LoanSummary, serial: LoanSummary) -> None:
    """Print a side-by-side comparison table of two loan summaries."""
    header = f"{'':30s} {'Annuity':>18s} {'Serial':>18s} {'Difference':>18s}"
    sep = "-" * len(header)

    print(f"\n{'LOAN COMPARISON':^{len(header)}}")
    print(sep)
    print(f"  Loan amount:            {format_nok(annuity.principal):>20s}")
    print(f"  Interest rate:          {annuity.annual_interest_rate*100:>19.2f}%")
    print(f"  Term:                   {annuity.term_years:>17d} yr")
    print(sep)
    print(header)
    print(sep)

    rows = [
        ("Total paid", annuity.total_paid, serial.total_paid),
        ("Total interest", annuity.total_interest, serial.total_interest),
        ("Total fees", annuity.total_fees, serial.total_fees),
        ("Tax deduction (22%)", annuity.total_tax_deduction, serial.total_tax_deduction),
        ("Net cost (after tax ded.)", annuity.total_net_cost, serial.total_net_cost),
    ]

    if annuity.total_rental_income_gross > 0:
        rows += [
            ("", 0, 0),  # spacer
            ("Rental income (gross)", annuity.total_rental_income_gross, serial.total_rental_income_gross),
            ("Rental tax", annuity.total_rental_tax, serial.total_rental_tax),
            ("Rental income (net)", annuity.total_rental_income_net, serial.total_rental_income_net),
            ("Net cost after rental", annuity.total_net_cost_after_rental, serial.total_net_cost_after_rental),
        ]

    for label, a_val, s_val in rows:
        if label == "":
            print()
            continue
        diff = a_val - s_val
        print(f"  {label:28s} {format_nok(a_val):>18s} {format_nok(s_val):>18s} {format_nok(diff):>18s}")

    print(sep)

    # First / last payment comparison
    print(f"\n  First monthly payment:   {format_nok(annuity.monthly_payments[0].total_payment):>18s}"
          f" {format_nok(serial.monthly_payments[0].total_payment):>18s}")
    print(f"  Last monthly payment:    {format_nok(annuity.monthly_payments[-1].total_payment):>18s}"
          f" {format_nok(serial.monthly_payments[-1].total_payment):>18s}")
    print()


def print_annual_schedule(summary: LoanSummary) -> None:
    """Print a year-by-year breakdown of a loan."""
    print(f"\n  Annual schedule – {summary.loan_type} loan")
    print(f"  {'Year':>4s}  {'Principal':>12s}  {'Interest':>12s}  {'Fees':>10s}"
          f"  {'Total paid':>12s}  {'Tax ded.':>12s}  {'Net cost':>12s}  {'Balance':>14s}")
    print("  " + "-" * 100)

    for a in summary.annual_summaries:
        print(f"  {a.year:>4d}  {format_nok(a.total_principal):>12s}  {format_nok(a.total_interest):>12s}"
              f"  {format_nok(a.total_fees):>10s}  {format_nok(a.total_payments):>12s}"
              f"  {format_nok(a.tax_deduction):>12s}  {format_nok(a.net_cost):>12s}"
              f"  {format_nok(a.remaining_balance):>14s}")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("  Norwegian Loan Calculator – Annuity vs Serial Loan Comparison")
    print("=" * 80)

    # Example: NOK 3,500,000 loan at 4.5% over 25 years with NOK 50/month fee
    loan = LoanParameters(
        principal=3_500_000,
        annual_interest_rate=0.045,
        term_years=25,
        extra_fees_per_month=50,
    )

    # Example: Renting out part of own home for NOK 8,000/month (tax-free)
    rental = RentalParameters(
        monthly_rental_income=8_000,
        is_short_term=False,
        owner_occupies_half=True,
        annual_maintenance_cost=0,
    )

    annuity, serial = compare_loans(loan, rental)
    print_comparison(annuity, serial)
    print_annual_schedule(annuity)
    print_annual_schedule(serial)
