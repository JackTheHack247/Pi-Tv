"""
Countries using DVB-T / DVB-T2 terrestrial broadcast.

Used to build the region menu. Channels come from live aerial scans only.
"""

from __future__ import annotations

# ISO 3166-1 alpha-2 codes
EUROPE = (
    "AL", "AD", "AM", "AT", "AZ", "BY", "BE", "BA", "BG", "HR", "CY", "CZ", "DK",
    "EE", "FI", "FR", "GE", "DE", "GR", "HU", "IS", "IE", "IT", "XK", "LV", "LI",
    "LT", "LU", "MT", "MD", "MC", "ME", "NL", "MK", "NO", "PL", "PT", "RO", "RU",
    "SM", "RS", "SK", "SI", "ES", "SE", "CH", "TR", "UA", "UK", "GB", "VA",
)

ASIA_MIDDLE_EAST = (
    "AF", "BH", "BD", "BT", "BN", "KH", "IN", "ID", "IR", "IQ", "IL", "JO", "KZ",
    "KW", "KG", "LB", "MY", "MN", "MM", "NP", "KP", "OM", "PS", "QA", "SA", "SG",
    "LK", "SY", "TW", "TJ", "TH", "TM", "AE", "UZ", "VN", "YE",
)

AFRICA = (
    "DZ", "AO", "BJ", "BF", "BI", "CM", "CV", "CF", "TD", "CG", "CD", "DJ", "EG",
    "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "CI", "KE", "LS", "LR",
    "LY", "MG", "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST",
    "SN", "SC", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "ZM", "ZW",
)

OCEANIA = ("AU", "FJ", "NZ", "PG", "WS", "SB", "TO", "VU")

AMERICAS = ("CO", "PA", "SR", "TT", "GF", "GP", "MQ")

ALL_DVB_COUNTRIES: frozenset[str] = frozenset(
    EUROPE + ASIA_MIDDLE_EAST + AFRICA + OCEANIA + AMERICAS
)

# Display names where ISO code differs from common name
COUNTRY_ALIASES: dict[str, str] = {
    "GB": "United Kingdom",
    "UK": "United Kingdom",
    "VA": "Vatican City",
    "MK": "North Macedonia",
    "XK": "Kosovo",
    "CI": "Ivory Coast",
    "SZ": "Eswatini",
    "CG": "Congo",
    "CD": "Democratic Republic of the Congo",
    "TR": "Turkiye",
    "GF": "French Guiana",
    "GP": "Guadeloupe",
    "MQ": "Martinique",
}
