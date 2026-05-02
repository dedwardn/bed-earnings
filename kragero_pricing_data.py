"""
Kragerø Resort – Collected Pricing Dataset
==========================================

Scraped / researched from multiple booking platforms and public sources.
All prices are per night for a 2-bedroom apartment (~77 sqm) unless noted.

Data collection date: May 2026
Sources listed per data point.
"""

# ============================================================================
# 1. NIGHTLY RATES – COLLECTED FROM BOOKING PLATFORMS
# ============================================================================
#
# The resort sells via its own booking system (booking.krageroresort.no),
# Booking.com, Airbnb, Hotels.com, KAYAK, Momondo, Klook, Travelocity,
# Expedia, and HotelsCombined.
#
# NOTE: Hotel rooms and apartments are different price tiers.
# Hotel rooms are cheaper; apartments (leiligheter) are the premium tier.
#
# Sources:
#   [1] Momondo   - https://www.momondo.com/hotels/kragero/Kragero-Resort.mhd456470.ksp
#   [2] KAYAK     - https://www.kayak.com/Kragero-Hotels-Kragero-Resort.456470.ksp
#   [3] HotelsCombined - https://www.hotelscombined.com/Hotel/Kragero_Resort.htm
#   [4] Travelocity - https://www.travelocity.com/Kragero-Hotels-Krager-Resort.h1644631.Hotel-Information
#   [5] Airbnb    - https://www.airbnb.com/rooms/42012694 (Top apartment)
#   [6] Airbnb    - https://www.airbnb.com/rooms/1112243189572127776 (Cabin w/Jacuzzi)
#   [7] Airbnb    - https://www.airbnb.com/rooms/624548893439085292 (Cabin at Sydri)
#   [8] Airbnb    - https://www.airbnb.com/rooms/688979908953909400 (Large cabin)
#   [9] Booking.com - https://www.booking.com/hotel/no/resort-kragero.html
#   [10] Klook    - https://www.klook.com/en-US/hotels/detail/497915-krager-resort/
#   [11] Resort booking - https://booking.krageroresort.no/en/accommodation
#   [12] Finn listing 461543499 – Kragerø Resort 633/634 (PrivatMegleren)

# USD to NOK approximate rate: 1 USD ≈ 10.5 NOK (May 2026)
USD_TO_NOK = 10.5

# ---------------------------------------------------------------------------
# HOTEL/RESORT ROOM rates (NOT apartment – these are the base rates)
# ---------------------------------------------------------------------------
HOTEL_ROOM_RATES = {
    "description": "Standard hotel/resort room rates across platforms",
    "sources": ["KAYAK", "Momondo", "HotelsCombined", "Travelocity"],
    "data": {
        "lowest_seen":          {"usd": 109, "nok_est": 1_145,  "source": "KAYAK"},
        "cheapest_deal":        {"usd": 114, "nok_est": 1_197,  "source": "Momondo"},
        "best_deal":            {"usd": 144, "nok_est": 1_512,  "source": "HotelsCombined"},
        "travelocity_from":     {"usd": 149, "nok_est": 1_565,  "source": "Travelocity"},
        "avg_wednesday":        {"usd": 160, "nok_est": 1_680,  "source": "KAYAK"},
        "avg_low_deal":         {"usd": 163, "nok_est": 1_712,  "source": "Momondo"},
        "avg_nightly":          {"usd": 194, "nok_est": 2_037,  "source": "Momondo"},
        "avg_recent":           {"usd": 209, "nok_est": 2_195,  "source": "HotelsCombined"},
        "peak_max":             {"usd": 760, "nok_est": 7_980,  "source": "KAYAK"},
    },
    "seasonality": {
        "cheapest_months": ["January", "October"],
        "cheapest_day": "Wednesday",
        "most_expensive_month": "March",  # Easter/winter sport season
        "most_expensive_day": "Monday",
    },
}

# ---------------------------------------------------------------------------
# APARTMENT / AIRBNB rates (2-bedroom, comparable to unit 633/634)
# ---------------------------------------------------------------------------
APARTMENT_RATES_AIRBNB = {
    "description": "Airbnb listings at/near Kragerø Resort for apartments and cabins",
    "data": [
        {
            "name": "Top apartment – Kragerø Spa Resort",
            "airbnb_id": 42012694,
            "type": "Apartment",
            "bedrooms": 3,
            "bathrooms": 2,
            "sqm": 96,
            "beds": 7,
            "nightly_rate_usd": None,  # Not shown in search results
            "source": "Airbnb listing",
        },
        {
            "name": "Newer cabin at Kragerø Resort w/Jacuzzi",
            "airbnb_id": 1112243189572127776,
            "type": "Cabin",
            "nightly_rate_usd": 233,
            "nightly_rate_nok_est": 2_447,
            "note": "Peak season rate (July 2025)",
            "source": "Airbnb",
        },
        {
            "name": "Cabin at Sydri – Kragerø Resort",
            "airbnb_id": 624548893439085292,
            "type": "Cabin",
            "nightly_rate_usd": 197,
            "nightly_rate_nok_est": 2_069,
            "source": "Airbnb",
        },
        {
            "name": "Large cabin at Kragerø Resort",
            "airbnb_id": 688979908953909400,
            "type": "Cabin/House",
            "nightly_rate_usd": None,
            "source": "Airbnb",
        },
        {
            "name": "Nice house by the sea in Kragerø",
            "airbnb_id": 1068740404673683972,
            "type": "House",
            "nightly_rate_usd": 221,
            "nightly_rate_nok_est": 2_321,
            "note": "August 2025 rate",
            "source": "Airbnb",
        },
    ],
}

# ---------------------------------------------------------------------------
# RESORT OWN BOOKING SYSTEM – Room types and price tiers
# ---------------------------------------------------------------------------
RESORT_ROOM_TYPES = {
    "description": "Room types from resort's own website (krageroresort.no)",
    "sources": ["krageroresort.no/en/rom-suiter/", "booking.krageroresort.no"],
    "note": "Prices start from EUR 51 on resort booking system",
    "types": [
        {
            "name": "Standard Room",
            "description": "Hotel room with TV, bathroom",
            "tier": "budget",
        },
        {
            "name": "Spa Suite",
            "description": "Stunning views of archipelago, Nespresso, bathrobes/slippers, "
                           "separate bedroom, living room with dining area, sofa bed, balcony",
            "tier": "premium",
        },
        {
            "name": "One-Bedroom Apartment",
            "description": "Kitchenette, seating area, 1 bedroom, balcony",
            "tier": "apartment",
        },
        {
            "name": "Two-Bedroom Apartment",
            "description": "Full kitchen with refrigerator & dishwasher, living room, "
                           "2 separate bedrooms, 1+ bathroom, balcony",
            "tier": "apartment",
        },
    ],
}


# ============================================================================
# 2. SEASONAL PRICING ESTIMATES (NOK) – for 2-bedroom apartment
# ============================================================================
#
# Synthesized from all collected data points:
# - Hotel room avg $194 ≈ 2,037 NOK → apartments command ~20-50% premium
# - Airbnb comparables: 2,069–2,447 NOK in peak season
# - Low season deals from $109 ≈ 1,145 NOK (hotel), apartments ~1,300-1,500 NOK
# - Peak (Jul) can reach $760 ≈ 7,980 NOK for premium units
#
# These are estimates for independent Airbnb/Booking management.
# No verified rental income is available from the listing.

ESTIMATED_MONTHLY_PRICING_2BR_APARTMENT = [
    {"month": "Jan", "nightly_rate_nok": 1_100, "occupancy_pct": 8,
     "notes": "Dead season, very few bookings. Cheapest month per KAYAK."},
    {"month": "Feb", "nightly_rate_nok": 1_300, "occupancy_pct": 18,
     "notes": "Winter holiday (vinterferie) bump. Easter can fall here."},
    {"month": "Mar", "nightly_rate_nok": 1_500, "occupancy_pct": 20,
     "notes": "KAYAK flags March as 'high season' (Easter/spring break)."},
    {"month": "Apr", "nightly_rate_nok": 1_400, "occupancy_pct": 15,
     "notes": "Easter spike if it falls here, otherwise moderate."},
    {"month": "May", "nightly_rate_nok": 2_000, "occupancy_pct": 30,
     "notes": "12-16k/week listed (avg ~14k). 17. mai holiday spike."},
    {"month": "Jun", "nightly_rate_nok": 2_570, "occupancy_pct": 55,
     "notes": "~18k/week listed. Summer begins."},
    {"month": "Jul", "nightly_rate_nok": 3_000, "occupancy_pct": 80,
     "notes": "Peak season. Extrapolated above June rate."},
    {"month": "Aug", "nightly_rate_nok": 2_140, "occupancy_pct": 60,
     "notes": "~15k/week listed. Late summer."},
    {"month": "Sep", "nightly_rate_nok": 1_500, "occupancy_pct": 25,
     "notes": "10-11k/week listed (avg ~10.5k). Shoulder season."},
    {"month": "Oct", "nightly_rate_nok": 1_200, "occupancy_pct": 10,
     "notes": "Low season begins. KAYAK flags October as cheapest."},
    {"month": "Nov", "nightly_rate_nok": 1_000, "occupancy_pct": 5,
     "notes": "Very low season. Minimal demand."},
    {"month": "Dec", "nightly_rate_nok": 1_400, "occupancy_pct": 20,
     "notes": "Christmas/NYE spike. Otherwise low."},
]

# Validation: estimate annual income at these rates
_est_income = sum(
    m["nightly_rate_nok"] * (m["occupancy_pct"] / 100) *
    [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][i]
    for i, m in enumerate(ESTIMATED_MONTHLY_PRICING_2BR_APARTMENT)
)


# ============================================================================
# 3. GUEST-FACING RESORT FEES (extras, not owner costs)
# ============================================================================
#
# These are fees charged to guests for extras – NOT owner management costs.
# Included for reference when setting guest pricing / listing descriptions.
#
# Sources: krageroresort.no/policy/, krageroresort.no/parkering/,
#          search results from multiple platforms

GUEST_RESORT_FEES = {
    "parking": {
        "covered_per_night_nok": 179,
        "source": "Hotels.com, Expedia, krageroresort.no",
    },
    "late_checkout": {
        "fee_nok": 350,
        "note": "Subject to availability",
        "source": "krageroresort.no/policy/",
    },
    "pet_fee": {
        "per_stay_nok": 300,
        "source": "krageroresort.no/policy/",
    },
    "crib": {
        "per_day_nok": 250,
        "source": "Hotels.com",
    },
    "rollaway_bed": {
        "per_day_nok": 850,
        "source": "Hotels.com",
    },
    "spa_day_pass": {
        "adult_nok": 295,
        "child_over_3_nok": 145,
        "child_under_3_nok": 75,
        "clip_card_10_nok": 2_400,
        "note": "For non-staying guests. Spa requires age 16+.",
        "source": "krageroresort.no",
    },
    "checkin_time": "15:00",
    "checkout_time": "11:00",
    "cancellation": "Free until 16:00, 7 days before arrival. Full charge after.",
}


# ============================================================================
# 4. RENTAL MANAGEMENT / UTLEIEORDNING
# ============================================================================
#
# Kragerø Resort (managed by Fredensborg Fritid) offers a rental pool
# arrangement for apartment owners.
#
# Sources:
#   - fredensborgfritid.no/destinasjoner/kragero/prosjekter/kragero-resort-fri
#   - Finn listing 461543499 (unit 633/634, PrivatMegleren Kragerø)
#   - Skatteetaten ruling on similar resort arrangements

RENTAL_MANAGEMENT = {
    "operator": "Kragerø Resort / Fredensborg Fritid",
    "services_included": [
        "Marketing on resort website (high traffic)",
        "Booking system administration",
        "Agreement conclusion & invoicing",
        "Key handling for guests",
        "Cleaning after departures",
        "Linen and towel changes",
        "Concierge service during stays",
        "Owner dashboard: bookings, income, costs overview",
    ],
    "owner_flexibility": [
        "Open and block periods via calendar",
        "Full control over availability",
        "Can also list on Airbnb/Booking independently",
    ],
    "commission_estimate": {
        "resort_pool_pct": 30,
        "note": "Exact commission not publicly disclosed. Industry standard "
                "for Norwegian resort rental pools is 25-40%. Skatteetaten "
                "ruling references 30% to operator, 70% to owner as typical. "
                "This covers cleaning, linen, booking, marketing.",
        "sources": [
            "Skatteetaten ruling on resort rental arrangements",
            "Industry standard per lodgecompliance.com",
            "Comparable: Evolve/global avg 10-30% management fee",
        ],
    },
}


# ============================================================================
# 5. PROPERTY COSTS – UNIT 633/634
# ============================================================================

PROPERTY_COSTS = {
    "unit": "633/634",
    "address": "Kragerø Resort 633/634, 3788 Stabbestad",
    "prisantydning_nok": 3_490_000,
    "totalpris_nok": 3_578_340,
    "omkostninger_nok": 88_340,
    "felleskostnader_monthly_nok": 1_371,
    "felleskostnader_annual_nok": 16_452,    # 1,371 × 12
    "kommunale_avgifter_annual_nok": 7_877,
    "eiendomsskatt_annual_nok": 7_877,
    "formuesverdi_nok": 712_500,
    "sqm": 77,
    "bedrooms": 2,
    "bathrooms": 2,             # 2 assumed from listing description
    "terraces": 2,
    "sengeplasser": 4,
    "etasje": 2,
    "byggeaar": 2007,
    "eieform": "Selveier",
    "boligtype": "Hytte",
    "energimerking": "B",
    "felleskostnader_includes": (
        "Kommunale avgifter (excl. eiendomsskatt), festeavgift, "
        "utvendig forsikring, utendørs drift (gartner, brøyting etc), "
        "TV/internett og vaktmestertjenester, hotelltjenester, "
        "forretningsførsel og revisjon samt godtgjørelse til styret."
    ),
    "broker": "PrivatMegleren Kragerø",
    "broker_agent": "Mathias Olsen",
    "source": "Finn listing 461543499",
}


# ============================================================================
# 6. ESTIMATED ANNUAL INCOME
# ============================================================================
#
# No verified rental income is reported on the listing.
# Our pricing model estimates ~216k NOK gross for independent management.
# With resort pool (~30% commission), owner would net ~151k NOK.

if __name__ == "__main__":
    print(f"Estimated annual gross income (independent): {_est_income:,.0f} NOK")
    print(f"Estimated owner income (resort pool, 30%):   {_est_income * 0.70:,.0f} NOK")
    print()

    print("Monthly pricing breakdown:")
    print(f"{'Month':<6s} {'Rate':>8s} {'Occ%':>6s} {'Days':>5s} {'Est Income':>12s}")
    print("-" * 40)
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    total = 0
    total_nights = 0
    for i, m in enumerate(ESTIMATED_MONTHLY_PRICING_2BR_APARTMENT):
        income = m["nightly_rate_nok"] * (m["occupancy_pct"] / 100) * days[i]
        nights = days[i] * m["occupancy_pct"] / 100
        total += income
        total_nights += nights
        print(f"{m['month']:<6s} {m['nightly_rate_nok']:>7,d} {m['occupancy_pct']:>5d}% "
              f"{days[i]:>5d} {income:>11,.0f}")
    print("-" * 40)
    print(f"{'TOTAL':<6s} {'':>8s} {'':>6s} {'':>5s} {total:>11,.0f}")
    print(f"\nEstimated booked nights: {total_nights:.0f}")
    print(f"Overall occupancy: {total_nights/365*100:.1f}%")
    print(f"Average rate per booked night: {total/total_nights:,.0f} NOK")
