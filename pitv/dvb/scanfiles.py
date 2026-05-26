"""Map countries to dtv-scan-tables DVB-T/T2 scan files."""

from __future__ import annotations

from pathlib import Path

DVB_T_ROOT = Path("/usr/share/dvb/dvb-t")

# Country code -> preferred scan table name (without path).
COUNTRY_SCAN_FILES: dict[str, str] = {
    "AD": "ad-All",
    "AR": "ar-All",
    "AT": "at-All",
    "AU": "au-All",
    "BE": "be-All",
    "BG": "bg-All",
    "BR": "br-All",
    "CA": "ca-All",
    "CH": "ch-All",
    "CZ": "cz-All",
    "DE": "de-All",
    "DK": "dk-All",
    "EE": "ee-All",
    "ES": "es-All",
    "FI": "fi-All",
    "FR": "fr-All",
    "GB": "uk-All",
    "GR": "gr-All",
    "HR": "hr-All",
    "HU": "hu-All",
    "IE": "ie-All",
    "IS": "is-All",
    "IT": "it-All",
    "LT": "lt-All",
    "LU": "lu-All",
    "LV": "lv-All",
    "NL": "nl-All",
    "NO": "no-All",
    "NZ": "nz-All",
    "PL": "pl-All",
    "PT": "pt-All",
    "RO": "ro-All",
    "RU": "ru-All",
    "SE": "se-All",
    "SI": "si-All",
    "SK": "sk-All",
    "TW": "tw-All",
    "UA": "ua-All",
    "UK": "uk-All",
    "US": "us-ATSC",
}


def scan_table_candidates(country_code: str) -> list[str]:
    code = country_code.upper()
    slug = code.lower()
    names = [
        COUNTRY_SCAN_FILES.get(code, ""),
        f"{slug}-All",
        slug,
        f"{slug}-Default",
    ]
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def resolve_scan_table(country_code: str) -> Path | None:
    if not DVB_T_ROOT.is_dir():
        return None
    for name in scan_table_candidates(country_code):
        path = DVB_T_ROOT / name
        if path.is_file():
            return path
    return None
