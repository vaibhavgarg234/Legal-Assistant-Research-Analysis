"""
L.A.R.A. Source & Statute Verification Engine
Validates that legal analyses do not cite repealed statutes as active law,
ensures cited URLs match real retrieved web evidence, and detects fabricated judgments.
"""

import re
from typing import List, Dict, Any

REPEALED_STATUTES = {
    "POTA": {
        "full_name": "POTA (Prevention of Terrorism Act, 2002)",
        "status": "REPEALED in 2004",
        "keywords": ["pota", "prevention of terrorism act"],
        "active_alternatives": ["UAPA (Unlawful Activities Prevention Act, 1967)", "Bharatiya Nyaya Sanhita (BNS)"],
    },
    "TADA": {
        "full_name": "TADA (Terrorist and Disruptive Activities (Prevention) Act, 1987)",
        "status": "LAPSED in 1995",
        "keywords": ["tada", "terrorist and disruptive activities"],
        "active_alternatives": ["UAPA", "BNS"],
    },

    "FERA": {
        "full_name": "Foreign Exchange Regulation Act, 1973",
        "status": "REPEALED in 1999",
        "keywords": ["fera", "foreign exchange regulation act"],
        "active_alternatives": ["FEMA (Foreign Exchange Management Act, 1999)"],
    },
    "COMPANIES_ACT_1956": {
        "full_name": "Companies Act, 1956",
        "status": "SUPERSEDED by Companies Act, 2013",
        "keywords": ["companies act 1956", "companies act, 1956"],
        "active_alternatives": ["Companies Act, 2013"],
    },
}

LANDMARK_VERIFIED_CASES = {
    "naveen jindal": "Union of India v. Naveen Jindal (2004) - Right to fly National Flag under Article 19(1)(a)",
    "dk basu": "D.K. Basu v. State of West Bengal (1997) - Guidelines on arrest and custody",
    "maneka gandhi": "Maneka Gandhi v. Union of India (1978) - Article 21 substantive due process",
    "kesavananda bharati": "Kesavananda Bharati v. State of Kerala (1973) - Basic Structure Doctrine",
    "puttaswamy": "K.S. Puttaswamy v. Union of India (2017) - Fundamental Right to Privacy",
    "shreya singhal": "Shreya Singhal v. Union of India (2015) - Freedom of Speech on Internet / Sec 66A IT Act",
    "arnesh kumar": "Arnesh Kumar v. State of Bihar (2014) - Restrictions on automatic arrest in offenses under 7 years",
    "swiss ribbons": "Swiss Ribbons Pvt. Ltd. v. Union of India (2019) - Constitutional validity of IBC",
    "vidya drolia": "Vidya Drolia v. Durga Trading Corp. (2020) - Arbitrability of disputes",
    "mazdoor kisan": "Mazdoor Kisan Shakti Sangathan v. Union of India (2018) - Right to protest at Jantar Mantar",
}


def verify_statutes(analysis_text: str) -> List[str]:
    """Detect if repealed statutes are cited as active law in recent contexts."""
    warnings = []
    text_lower = analysis_text.lower()

    for key, data in REPEALED_STATUTES.items():
        for kw in data["keywords"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                # Check if it was appropriately cited as historical/repealed
                history_mentions = ["repealed", "lapsed", "former", "historical", "prior to", "replaced"]
                is_flagged_historical = any(h in text_lower for h in history_mentions)
                if not is_flagged_historical:
                    warnings.append(
                        f"Repealed Statute Warning: {data['full_name']} was {data['status']}. "
                        f"Active alternative: {', '.join(data['active_alternatives'])}."
                    )
                break
    return warnings


def verify_urls(analysis_text: str, retrieved_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify that URLs cited in the analysis text match actual retrieved sources."""
    # Find all URLs in analysis
    url_pattern = re.compile(r"https?://[^\s\)\],;\"']+")
    cited_urls = set(url_pattern.findall(analysis_text))

    valid_urls = set()
    for s in retrieved_sources:
        if s.get("type") == "web" and s.get("url"):
            valid_urls.add(s["url"].rstrip("/"))

    verified = []
    unverified = []

    for u in cited_urls:
        clean_u = u.rstrip("/")
        # Check direct match or domain match
        if any(clean_u in v or v in clean_u for v in valid_urls):
            verified.append(u)
        else:
            unverified.append(u)

    return {
        "cited_urls": list(cited_urls),
        "verified_urls": verified,
        "unverified_urls": unverified,
    }


def verify_case_citations(analysis_text: str, research_context: str) -> List[str]:
    """
    Detect case citations in the analysis and verify whether they are supported
    by the research context or match recognized landmark jurisprudence.
    """
    warnings = []
    context_lower = research_context.lower()

    # Regex to capture case name patterns like "X v. Y" or "X vs Y"
    case_pattern = re.compile(r"([A-Z][A-Za-z0-9\.\s]+)\s+(?:v\.|vs\.?)\s+([A-Z][A-Za-z0-9\.\s]+)", re.MULTILINE)
    matches = case_pattern.findall(analysis_text)

    for p1, p2 in matches:
        case_phrase = f"{p1.strip()} v. {p2.strip()}"
        case_lower = case_phrase.lower()

        # Check if it is a recognized landmark case
        is_known_landmark = any(k in case_lower for k in LANDMARK_VERIFIED_CASES)

        # Check if it was present in retrieved research context
        is_in_context = (p1.strip().lower() in context_lower) and (p2.strip().lower() in context_lower)

        if not is_known_landmark and not is_in_context:
            warnings.append(
                f"Unverified Judicial Citation: '{case_phrase}' is not found in the retrieved evidence or landmark corpus."
            )

    return warnings


def run_source_verification(
    analysis_text: str,
    research_context: str,
    retrieved_sources: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Complete source verification pipeline returning pass/fail and badges.
    """
    statute_warnings = verify_statutes(analysis_text)
    url_results = verify_urls(analysis_text, retrieved_sources)
    case_warnings = verify_case_citations(analysis_text, research_context)

    has_fatal_statute_error = len(statute_warnings) > 0
    has_unverified_urls = len(url_results["unverified_urls"]) > 0

    passed = not has_fatal_statute_error and len(case_warnings) == 0

    # Format human-readable summary badge
    badge_lines = ["\n--- Source & Statute Verification ---"]
    if not statute_warnings:
        badge_lines.append("🛡️ Legislation Integrity: PASS (No repealed or superseded statutes misattributed)")
    else:
        for w in statute_warnings:
            badge_lines.append(f"⚠️ Legislation Integrity: FAIL ({w})")

    if not case_warnings:
        badge_lines.append("⚖️ Case Law Grounding: PASS (All cited judicial precedents are verified)")
    else:
        for cw in case_warnings:
            badge_lines.append(f"⚠️ Case Law Grounding: CAUTION ({cw})")

    verified_url_count = len(url_results["verified_urls"])
    if verified_url_count > 0:
        badge_lines.append(f"🔗 Live Evidence Traceability: PASS ({verified_url_count} verified web sources cited)")
    elif len(url_results["cited_urls"]) == 0 and len(retrieved_sources) > 0:
        badge_lines.append("ℹ️ Live Evidence Traceability: General statutory analysis without direct external web links")
    else:
        badge_lines.append(f"⚠️ Live Evidence Traceability: {len(url_results['unverified_urls'])} unverified external links")

    verification_badge = "\n".join(badge_lines)

    return {
        "passed": passed,
        "statute_warnings": statute_warnings,
        "case_warnings": case_warnings,
        "url_verification": url_results,
        "verification_badge": verification_badge,
    }
