"""
Short-Term Rental Investment Analysis – Norway
===============================================

Financial model for short-term (Airbnb/Booking) rental of holiday properties
under Norwegian tax law.

Norwegian tax rules applied (2025):
- Korttidsutleie threshold: first NOK 15,000/year tax-free per property
- 85% of income above threshold is taxable as ordinary income
- Tax rate on ordinary income: 22%
- No itemized deductions when using the 15,000 + 85% template
- If property is rented full-time (not owner-used): full deductions allowed
- VAT registration required if business turnover > NOK 50,000/12 months
- VAT rate on short-term accommodation: 12%
- Business classification triggers at ~5+ units or ~500+ sqm

Sources:
- Skatteetaten (Norwegian Tax Administration)
- Airbnb Tax Guide 2025 Norway
- BnbUtleie.no skatteregler 2025
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import math


# ---------------------------------------------------------------------------
# Constants – Norwegian tax parameters (2025)
# ---------------------------------------------------------------------------
SHORT_TERM_TAX_FREE_THRESHOLD = 15_000   # NOK per property per year
SHORT_TERM_TAXABLE_SHARE = 0.85          # 85% of income above threshold
ORDINARY_INCOME_TAX_RATE = 0.22          # Skatt på alminnelig inntekt
INTEREST_TAX_DEDUCTION_RATE = 0.22       # Rentefradrag
VAT_ACCOMMODATION_RATE = 0.12            # 12% MVA on short-term rental
VAT_REGISTRATION_THRESHOLD = 50_000      # Must register for VAT above this


class PricingModel(Enum):
    HIGH_LOW_SEASON = "high_low"
    MONTHLY = "monthly"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PropertyDetails:
    """The property being analyzed."""
    name: str
    purchase_price: float              # Total acquisition cost (inkl. omkostninger)
    sqm: float
    bedrooms: int
    bathrooms: int
    monthly_fees: float                # Felleskostnader per month
    annual_property_tax: float = 0.0   # Eiendomsskatt
    annual_insurance: float = 0.0
    annual_maintenance: float = 0.0    # Vedlikehold
    annual_utilities: float = 0.0      # Strøm, internett, etc. borne by owner
    formuesverdi: float = 0.0          # For wealth tax calculation


@dataclass
class HighLowSeasonPricing:
    """Simple two-season pricing model."""
    high_season_nightly_rate: float     # NOK per night (June–August typically)
    low_season_nightly_rate: float      # NOK per night (rest of year)
    shoulder_nightly_rate: float = 0.0  # Optional shoulder season rate
    high_season_months: int = 3         # Number of high season months
    shoulder_season_months: int = 2     # Number of shoulder season months
    high_season_occupancy: float = 0.70 # 70% occupancy in high season
    low_season_occupancy: float = 0.20  # 20% occupancy in low season
    shoulder_occupancy: float = 0.40    # 40% occupancy in shoulder season
    cleaning_fee_per_stay: float = 0.0  # Cleaning fee charged to guest
    avg_stay_nights: float = 3.0        # Average booking length


@dataclass
class MonthlyPricing:
    """Variable month-by-month pricing model."""
    months: list[dict]  # [{"month": "Jan", "nightly_rate": X, "occupancy": Y}, ...]
    cleaning_fee_per_stay: float = 0.0
    avg_stay_nights: float = 3.0


@dataclass
class OperatingCosts:
    """Costs incurred per rental operation."""
    platform_commission_rate: float = 0.03    # Airbnb host fee ~3%
    cleaning_cost_per_turnover: float = 800   # NOK per cleaning
    laundry_per_turnover: float = 200         # NOK
    consumables_per_turnover: float = 150     # Toiletries, coffee, etc.
    annual_furnishing_refresh: float = 10_000 # Replacement of worn items
    annual_marketing: float = 0               # Extra marketing costs
    property_management_rate: float = 0.0     # % of revenue if using manager


@dataclass
class LoanDetails:
    """Loan financing for the property."""
    loan_amount: float
    annual_interest_rate: float
    term_years: int
    loan_type: str = "annuity"   # "annuity" or "serial"


@dataclass
class MonthBreakdown:
    """Revenue and cost breakdown for a single month."""
    month: str
    month_num: int
    days: int
    nightly_rate: float
    occupancy: float
    booked_nights: float
    num_turnovers: float
    gross_rental_income: float
    cleaning_fee_income: float
    platform_fees: float
    cleaning_costs: float
    laundry_costs: float
    consumable_costs: float
    net_rental_income: float


@dataclass
class AnnualInvestmentSummary:
    """Complete annual financial summary."""
    # Revenue
    gross_rental_income: float
    cleaning_fee_income: float
    total_gross_income: float

    # Operating costs
    platform_fees: float
    cleaning_costs: float
    laundry_costs: float
    consumable_costs: float
    furnishing_refresh: float
    marketing_costs: float
    property_management_fees: float
    total_operating_costs: float

    # Property costs
    felleskostnader: float
    property_tax: float
    insurance: float
    maintenance: float
    utilities: float
    total_property_costs: float

    # Financing
    annual_interest: float
    annual_principal: float
    annual_loan_payment: float
    interest_tax_deduction: float

    # Tax
    taxable_rental_income: float
    rental_income_tax: float
    requires_vat_registration: bool
    vat_amount: float

    # Net results
    net_operating_income: float   # NOI = gross - operating - property costs
    pre_tax_cashflow: float       # NOI - loan payments
    post_tax_cashflow: float      # After all taxes and deductions
    total_annual_cost: float      # Everything you pay out
    effective_monthly_cost: float  # What it costs you per month to own

    # Yield metrics
    gross_yield: float            # Gross income / purchase price
    net_yield: float              # NOI / purchase price
    cap_rate: float               # NOI / purchase price (same as net yield for unlevered)
    cash_on_cash_return: float    # Post-tax cashflow / equity invested
    cost_per_own_night: float     # Cost per night you use it yourself

    # Breakdowns
    monthly_breakdown: list[MonthBreakdown]
    booked_nights_total: float
    available_nights: int
    own_use_nights: int
    overall_occupancy: float


# ---------------------------------------------------------------------------
# Month definitions
# ---------------------------------------------------------------------------
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Default seasonal classification for Norwegian coastal resort
DEFAULT_HIGH_MONTHS = {6, 7, 8}       # Jun, Jul, Aug
DEFAULT_SHOULDER_MONTHS = {5, 9}       # May, Sep
# Remaining months = low season


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def _build_monthly_schedule_high_low(
    pricing: HighLowSeasonPricing,
    own_use_nights: int = 0,
) -> list[MonthBreakdown]:
    """Build month-by-month schedule from high/low/shoulder season model."""

    # Distribute own-use nights across low season months first
    own_remaining = own_use_nights
    own_per_month = {}
    low_months_list = [m for m in range(1, 13)
                       if m not in DEFAULT_HIGH_MONTHS and m not in DEFAULT_SHOULDER_MONTHS]

    for m in low_months_list + list(DEFAULT_SHOULDER_MONTHS) + list(DEFAULT_HIGH_MONTHS):
        take = min(own_remaining, MONTH_DAYS[m - 1])
        own_per_month[m] = take
        own_remaining -= take
        if own_remaining <= 0:
            break

    months = []
    for i in range(12):
        m_num = i + 1
        days = MONTH_DAYS[i]
        own = own_per_month.get(m_num, 0)
        available = days - own

        if m_num in DEFAULT_HIGH_MONTHS:
            rate = pricing.high_season_nightly_rate
            occ = pricing.high_season_occupancy
        elif m_num in DEFAULT_SHOULDER_MONTHS:
            rate = pricing.shoulder_nightly_rate if pricing.shoulder_nightly_rate > 0 \
                else (pricing.high_season_nightly_rate + pricing.low_season_nightly_rate) / 2
            occ = pricing.shoulder_occupancy
        else:
            rate = pricing.low_season_nightly_rate
            occ = pricing.low_season_occupancy

        booked = available * occ
        turnovers = booked / pricing.avg_stay_nights if pricing.avg_stay_nights > 0 else 0
        gross = booked * rate
        cleaning_income = turnovers * pricing.cleaning_fee_per_stay

        months.append(MonthBreakdown(
            month=MONTH_NAMES[i],
            month_num=m_num,
            days=days,
            nightly_rate=rate,
            occupancy=occ,
            booked_nights=round(booked, 1),
            num_turnovers=round(turnovers, 1),
            gross_rental_income=round(gross, 0),
            cleaning_fee_income=round(cleaning_income, 0),
            platform_fees=0,
            cleaning_costs=0,
            laundry_costs=0,
            consumable_costs=0,
            net_rental_income=0,
        ))

    return months


def _build_monthly_schedule_monthly(
    pricing: MonthlyPricing,
    own_use_nights: int = 0,
) -> list[MonthBreakdown]:
    """Build month-by-month schedule from explicit monthly pricing."""

    own_remaining = own_use_nights
    months = []
    for i, mp in enumerate(pricing.months):
        days = MONTH_DAYS[i]
        own = min(own_remaining, days)
        own_remaining = max(0, own_remaining - own)
        available = days - own

        rate = mp.get("nightly_rate", 0)
        occ = mp.get("occupancy", 0)
        booked = available * occ
        turnovers = booked / pricing.avg_stay_nights if pricing.avg_stay_nights > 0 else 0
        gross = booked * rate
        cleaning_income = turnovers * pricing.cleaning_fee_per_stay

        months.append(MonthBreakdown(
            month=MONTH_NAMES[i],
            month_num=i + 1,
            days=days,
            nightly_rate=rate,
            occupancy=occ,
            booked_nights=round(booked, 1),
            num_turnovers=round(turnovers, 1),
            gross_rental_income=round(gross, 0),
            cleaning_fee_income=round(cleaning_income, 0),
            platform_fees=0,
            cleaning_costs=0,
            laundry_costs=0,
            consumable_costs=0,
            net_rental_income=0,
        ))

    return months


def calculate_investment(
    prop: PropertyDetails,
    pricing: HighLowSeasonPricing | MonthlyPricing,
    ops: OperatingCosts,
    loan: Optional[LoanDetails] = None,
    own_use_nights: int = 30,
    equity: Optional[float] = None,
) -> AnnualInvestmentSummary:
    """
    Calculate a complete annual investment analysis for a short-term rental property.

    Args:
        prop: Property details
        pricing: Either HighLowSeasonPricing or MonthlyPricing
        ops: Operating cost assumptions
        loan: Optional loan details (None = all-cash purchase)
        own_use_nights: Nights per year you use the property yourself
        equity: Cash invested (defaults to purchase_price - loan_amount)
    """

    # --- Build monthly schedule ---
    if isinstance(pricing, HighLowSeasonPricing):
        month_schedule = _build_monthly_schedule_high_low(pricing, own_use_nights)
    else:
        month_schedule = _build_monthly_schedule_monthly(pricing, own_use_nights)

    # --- Apply operating costs to each month ---
    for mb in month_schedule:
        mb.platform_fees = round(mb.gross_rental_income * ops.platform_commission_rate, 0)
        mb.cleaning_costs = round(mb.num_turnovers * ops.cleaning_cost_per_turnover, 0)
        mb.laundry_costs = round(mb.num_turnovers * ops.laundry_per_turnover, 0)
        mb.consumable_costs = round(mb.num_turnovers * ops.consumables_per_turnover, 0)
        mb.net_rental_income = round(
            mb.gross_rental_income + mb.cleaning_fee_income
            - mb.platform_fees - mb.cleaning_costs
            - mb.laundry_costs - mb.consumable_costs, 0)

    # --- Aggregate annual figures ---
    gross_rental = sum(m.gross_rental_income for m in month_schedule)
    cleaning_income = sum(m.cleaning_fee_income for m in month_schedule)
    total_gross = gross_rental + cleaning_income

    platform_fees = sum(m.platform_fees for m in month_schedule)
    cleaning_costs = sum(m.cleaning_costs for m in month_schedule)
    laundry_costs = sum(m.laundry_costs for m in month_schedule)
    consumable_costs = sum(m.consumable_costs for m in month_schedule)
    mgmt_fees = total_gross * ops.property_management_rate
    total_ops = (platform_fees + cleaning_costs + laundry_costs + consumable_costs
                 + ops.annual_furnishing_refresh + ops.annual_marketing + mgmt_fees)

    # Property costs
    felles = prop.monthly_fees * 12
    total_prop = felles + prop.annual_property_tax + prop.annual_insurance + \
                 prop.annual_maintenance + prop.annual_utilities

    # Financing
    annual_interest = 0.0
    annual_principal = 0.0
    annual_loan_payment = 0.0
    if loan:
        if loan.loan_type == "annuity":
            mr = loan.annual_interest_rate / 12
            n = loan.term_years * 12
            if mr > 0:
                monthly_pmt = loan.loan_amount * (mr * (1 + mr) ** n) / ((1 + mr) ** n - 1)
            else:
                monthly_pmt = loan.loan_amount / n
            annual_loan_payment = monthly_pmt * 12
            annual_interest = loan.loan_amount * loan.annual_interest_rate  # first year approx
            annual_principal = annual_loan_payment - annual_interest
        else:  # serial
            annual_principal = loan.loan_amount / loan.term_years
            annual_interest = loan.loan_amount * loan.annual_interest_rate  # first year
            annual_loan_payment = annual_principal + annual_interest

    interest_deduction = annual_interest * INTEREST_TAX_DEDUCTION_RATE

    # --- Tax calculation (korttidsutleie template) ---
    # Gross rental income for tax purposes (cleaning fees are income too)
    tax_gross = total_gross
    if tax_gross <= SHORT_TERM_TAX_FREE_THRESHOLD:
        taxable = 0.0
    else:
        taxable = (tax_gross - SHORT_TERM_TAX_FREE_THRESHOLD) * SHORT_TERM_TAXABLE_SHARE
    rental_tax = taxable * ORDINARY_INCOME_TAX_RATE

    # VAT check
    requires_vat = tax_gross > VAT_REGISTRATION_THRESHOLD
    vat_amount = 0.0  # Simplified: assuming not VAT-registered for personal use

    # --- Net results ---
    noi = total_gross - total_ops - total_prop
    pre_tax_cf = noi - annual_loan_payment
    post_tax_cf = pre_tax_cf - rental_tax + interest_deduction

    total_annual_cost = total_ops + total_prop + annual_loan_payment + rental_tax - interest_deduction - total_gross
    effective_monthly = total_annual_cost / 12

    # --- Yield metrics ---
    if equity is None:
        equity = prop.purchase_price - (loan.loan_amount if loan else 0)
    equity = max(equity, 1)  # avoid division by zero

    gross_yield = total_gross / prop.purchase_price
    net_yield = noi / prop.purchase_price
    cap_rate = net_yield
    cash_on_cash = post_tax_cf / equity

    booked_total = sum(m.booked_nights for m in month_schedule)
    available = 365 - own_use_nights
    overall_occ = booked_total / available if available > 0 else 0

    # Cost per own-use night (what does it cost you per night you use it?)
    if own_use_nights > 0:
        cost_own_night = max(0, -post_tax_cf) / own_use_nights
    else:
        cost_own_night = 0

    return AnnualInvestmentSummary(
        gross_rental_income=round(gross_rental),
        cleaning_fee_income=round(cleaning_income),
        total_gross_income=round(total_gross),
        platform_fees=round(platform_fees),
        cleaning_costs=round(cleaning_costs),
        laundry_costs=round(laundry_costs),
        consumable_costs=round(consumable_costs),
        furnishing_refresh=round(ops.annual_furnishing_refresh),
        marketing_costs=round(ops.annual_marketing),
        property_management_fees=round(mgmt_fees),
        total_operating_costs=round(total_ops),
        felleskostnader=round(felles),
        property_tax=round(prop.annual_property_tax),
        insurance=round(prop.annual_insurance),
        maintenance=round(prop.annual_maintenance),
        utilities=round(prop.annual_utilities),
        total_property_costs=round(total_prop),
        annual_interest=round(annual_interest),
        annual_principal=round(annual_principal),
        annual_loan_payment=round(annual_loan_payment),
        interest_tax_deduction=round(interest_deduction),
        taxable_rental_income=round(taxable),
        rental_income_tax=round(rental_tax),
        requires_vat_registration=requires_vat,
        vat_amount=round(vat_amount),
        net_operating_income=round(noi),
        pre_tax_cashflow=round(pre_tax_cf),
        post_tax_cashflow=round(post_tax_cf),
        total_annual_cost=round(total_annual_cost),
        effective_monthly_cost=round(effective_monthly),
        gross_yield=round(gross_yield, 4),
        net_yield=round(net_yield, 4),
        cap_rate=round(cap_rate, 4),
        cash_on_cash_return=round(cash_on_cash, 4),
        cost_per_own_night=round(cost_own_night),
        monthly_breakdown=month_schedule,
        booked_nights_total=round(booked_total, 1),
        available_nights=available,
        own_use_nights=own_use_nights,
        overall_occupancy=round(overall_occ, 3),
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_nok(amount: float) -> str:
    if amount < 0:
        return f"-{abs(amount):,.0f} kr".replace(",", " ")
    return f"{amount:,.0f} kr".replace(",", " ")


def format_pct(val: float) -> str:
    return f"{val * 100:.1f}%"


def print_investment_summary(summary: AnnualInvestmentSummary, prop: PropertyDetails) -> None:
    """Print a comprehensive investment analysis report."""
    w = 80
    print()
    print("=" * w)
    print(f"  SHORT-TERM RENTAL INVESTMENT ANALYSIS".center(w))
    print(f"  {prop.name}".center(w))
    print("=" * w)

    print(f"\n  Purchase price:         {format_nok(prop.purchase_price):>20s}")
    print(f"  Size:                   {prop.sqm:>17.0f} sqm")
    print(f"  Bedrooms / Bathrooms:   {prop.bedrooms:>11d} / {prop.bathrooms}")

    # --- Monthly breakdown table ---
    print(f"\n  {'MONTHLY BREAKDOWN':^{w-4}}")
    print("  " + "-" * (w - 4))
    print(f"  {'Month':<5s} {'Rate':>8s} {'Occ%':>6s} {'Nights':>7s} {'Turns':>6s}"
          f" {'Gross':>10s} {'OpCost':>10s} {'Net':>10s}")
    print("  " + "-" * (w - 4))

    for m in summary.monthly_breakdown:
        op_cost = m.platform_fees + m.cleaning_costs + m.laundry_costs + m.consumable_costs
        print(f"  {m.month:<5s} {format_nok(m.nightly_rate):>8s} {m.occupancy*100:>5.0f}%"
              f" {m.booked_nights:>7.1f} {m.num_turnovers:>6.1f}"
              f" {format_nok(m.gross_rental_income):>10s}"
              f" {format_nok(op_cost):>10s}"
              f" {format_nok(m.net_rental_income):>10s}")

    print("  " + "-" * (w - 4))
    total_op = summary.platform_fees + summary.cleaning_costs + summary.laundry_costs + summary.consumable_costs
    print(f"  {'TOTAL':<5s} {'':>8s} {summary.overall_occupancy*100:>5.1f}%"
          f" {summary.booked_nights_total:>7.1f} {'':>6s}"
          f" {format_nok(summary.gross_rental_income):>10s}"
          f" {format_nok(total_op):>10s}"
          f" {format_nok(summary.total_gross_income - total_op):>10s}")

    # --- Revenue summary ---
    print(f"\n  {'REVENUE':^{w-4}}")
    print("  " + "-" * (w - 4))
    print(f"  Gross rental income:         {format_nok(summary.gross_rental_income):>18s}")
    print(f"  Cleaning fee income:         {format_nok(summary.cleaning_fee_income):>18s}")
    print(f"  Total gross income:          {format_nok(summary.total_gross_income):>18s}")

    # --- Operating costs ---
    print(f"\n  {'OPERATING COSTS':^{w-4}}")
    print("  " + "-" * (w - 4))
    print(f"  Platform commission:         {format_nok(summary.platform_fees):>18s}")
    print(f"  Cleaning:                    {format_nok(summary.cleaning_costs):>18s}")
    print(f"  Laundry:                     {format_nok(summary.laundry_costs):>18s}")
    print(f"  Consumables:                 {format_nok(summary.consumable_costs):>18s}")
    print(f"  Furnishing refresh:          {format_nok(summary.furnishing_refresh):>18s}")
    if summary.marketing_costs:
        print(f"  Marketing:                   {format_nok(summary.marketing_costs):>18s}")
    if summary.property_management_fees:
        print(f"  Property management:         {format_nok(summary.property_management_fees):>18s}")
    print(f"  Total operating costs:       {format_nok(summary.total_operating_costs):>18s}")

    # --- Property costs ---
    print(f"\n  {'PROPERTY COSTS':^{w-4}}")
    print("  " + "-" * (w - 4))
    print(f"  Felleskostnader (12 mo):     {format_nok(summary.felleskostnader):>18s}")
    if summary.property_tax:
        print(f"  Property tax:                {format_nok(summary.property_tax):>18s}")
    if summary.insurance:
        print(f"  Insurance:                   {format_nok(summary.insurance):>18s}")
    if summary.maintenance:
        print(f"  Maintenance:                 {format_nok(summary.maintenance):>18s}")
    if summary.utilities:
        print(f"  Utilities:                   {format_nok(summary.utilities):>18s}")
    print(f"  Total property costs:        {format_nok(summary.total_property_costs):>18s}")

    # --- Financing ---
    if summary.annual_loan_payment > 0:
        print(f"\n  {'FINANCING':^{w-4}}")
        print("  " + "-" * (w - 4))
        print(f"  Annual interest:             {format_nok(summary.annual_interest):>18s}")
        print(f"  Annual principal:            {format_nok(summary.annual_principal):>18s}")
        print(f"  Total loan payments:         {format_nok(summary.annual_loan_payment):>18s}")
        print(f"  Interest tax deduction:     -{format_nok(summary.interest_tax_deduction):>17s}")

    # --- Tax ---
    print(f"\n  {'TAX (Korttidsutleie Template)':^{w-4}}")
    print("  " + "-" * (w - 4))
    print(f"  Gross rental income:         {format_nok(summary.total_gross_income):>18s}")
    print(f"  Tax-free threshold:         -{format_nok(SHORT_TERM_TAX_FREE_THRESHOLD):>17s}")
    print(f"  Taxable (85% of excess):     {format_nok(summary.taxable_rental_income):>18s}")
    print(f"  Tax (22%):                   {format_nok(summary.rental_income_tax):>18s}")
    if summary.requires_vat_registration:
        print(f"  *** VAT registration likely required (income > {format_nok(VAT_REGISTRATION_THRESHOLD)}) ***")

    # --- Net results ---
    print(f"\n  {'NET RESULTS':^{w-4}}")
    print("  " + "-" * (w - 4))
    print(f"  Net operating income (NOI):  {format_nok(summary.net_operating_income):>18s}")
    if summary.annual_loan_payment > 0:
        print(f"  Pre-tax cashflow:            {format_nok(summary.pre_tax_cashflow):>18s}")
    print(f"  Post-tax cashflow:           {format_nok(summary.post_tax_cashflow):>18s}")
    print()
    if summary.total_annual_cost > 0:
        print(f"  Annual net cost to you:      {format_nok(summary.total_annual_cost):>18s}")
        print(f"  Monthly net cost to you:     {format_nok(summary.effective_monthly_cost):>18s}")
    else:
        print(f"  Annual net profit:           {format_nok(-summary.total_annual_cost):>18s}")
        print(f"  Monthly net profit:          {format_nok(-summary.effective_monthly_cost):>18s}")

    # --- Key metrics ---
    print(f"\n  {'KEY METRICS':^{w-4}}")
    print("  " + "-" * (w - 4))
    print(f"  Booked nights:               {summary.booked_nights_total:>14.0f} nights")
    print(f"  Own use:                     {summary.own_use_nights:>14d} nights")
    print(f"  Overall occupancy:           {format_pct(summary.overall_occupancy):>18s}")
    print(f"  Gross yield:                 {format_pct(summary.gross_yield):>18s}")
    print(f"  Net yield (cap rate):        {format_pct(summary.net_yield):>18s}")
    if summary.annual_loan_payment > 0:
        print(f"  Cash-on-cash return:         {format_pct(summary.cash_on_cash_return):>18s}")
    if summary.own_use_nights > 0 and summary.total_annual_cost > 0:
        print(f"  Cost per own-use night:      {format_nok(summary.cost_per_own_night):>18s}")

    print("=" * w)
    print()


# ---------------------------------------------------------------------------
# Scenario comparison
# ---------------------------------------------------------------------------

def compare_scenarios(
    prop: PropertyDetails,
    scenarios: dict[str, tuple],
    ops: OperatingCosts,
    loan: Optional[LoanDetails] = None,
) -> dict[str, AnnualInvestmentSummary]:
    """
    Compare multiple rental scenarios.

    Args:
        scenarios: dict of {"name": (pricing, own_use_nights)} pairs
    """
    results = {}
    for name, (pricing, own_use) in scenarios.items():
        results[name] = calculate_investment(prop, pricing, ops, loan, own_use)
    return results


def print_scenario_comparison(results: dict[str, AnnualInvestmentSummary]) -> None:
    """Print a side-by-side comparison of multiple scenarios."""
    names = list(results.keys())
    col_w = 18

    header = f"  {'Metric':<30s}" + "".join(f" {n:>{col_w}s}" for n in names)
    sep = "-" * len(header)

    print(f"\n{'SCENARIO COMPARISON':^{len(header)}}")
    print(sep)

    rows = [
        ("Gross income", lambda s: s.total_gross_income),
        ("Operating costs", lambda s: s.total_operating_costs),
        ("Property costs", lambda s: s.total_property_costs),
        ("NOI", lambda s: s.net_operating_income),
        ("Rental tax", lambda s: s.rental_income_tax),
        ("Loan payments", lambda s: s.annual_loan_payment),
        ("Interest deduction", lambda s: s.interest_tax_deduction),
        ("Post-tax cashflow", lambda s: s.post_tax_cashflow),
        ("", None),
        ("Booked nights", lambda s: s.booked_nights_total),
        ("Own-use nights", lambda s: s.own_use_nights),
        ("Overall occupancy", lambda s: s.overall_occupancy),
        ("Gross yield", lambda s: s.gross_yield),
        ("Net yield", lambda s: s.net_yield),
        ("Cash-on-cash return", lambda s: s.cash_on_cash_return),
    ]

    for label, fn in rows:
        if fn is None:
            print()
            continue
        vals = [fn(results[n]) for n in names]
        if label in ("Overall occupancy", "Gross yield", "Net yield", "Cash-on-cash return"):
            formatted = [f"{v*100:.1f}%" for v in vals]
        elif label in ("Booked nights", "Own-use nights"):
            formatted = [f"{v:.0f}" for v in vals]
        else:
            formatted = [format_nok(v) for v in vals]
        line = f"  {label:<30s}" + "".join(f" {f:>{col_w}s}" for f in formatted)
        print(line)

    print(sep)
    print()
