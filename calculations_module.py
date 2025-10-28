# calculations_module.py - Corrected billing calculations
"""
Performs financial calculations for insurance claims.

CRITICAL FORMULA (per your Excel layout):
- Column D: Client Copay (client payment)
- Column E: Deductible being met (client payment)  
- Column F: Insurance Paid
- Column G: Insurance Contract Amount = D + E + F
- Column H: 65% Counselor Contracted rate = G × 0.65
- Column I: Amount to Counselor (copay and deductible subtracted) = F - (D + E)
- Column J: 35% Amount Paid to GWC per claim = G × 0.35
- Column K: Total payout to Counselor = Running sum of Column I

IMPORTANT: Provider adjustments (CO codes) are NOT included in patient responsibility.
Only PR codes create patient responsibility (copay/deductible).
"""

from typing import Dict, Union, Optional


def safe_float(value: Union[str, float, int]) -> float:
    """Safely convert a value to float. Returns 0.0 if invalid or missing."""
    if value is None or value in ("", "NOTFOUND", "N/A"):
        return 0.0
    try:
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").strip()
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def calculate_all(data: Dict[str, Union[str, float]]) -> Dict[str, Union[float, str, bool, list]]:
    """
    Perform all financial calculations for a single claim.
    
    Business Logic (per Excel layout):
    1. Contracted Insurance Rate (G) = Copay (D) + Deductible (E) + Insurance Paid (F)
    2. 65% Counselor Share (H) = 65% of G
    3. Amount to Counselor (I) = F - (D + E)  [Insurance Paid minus patient responsibility]
    4. 35% GWC Share (J) = 35% of G
    5. Total Payout to Counselor (K) = Running sum of column I
    
    Args:
        data: Dictionary with claim data including:
            - Copay: str/float (Column D) - from PR-3, PR-2, or other PR codes
            - Deductible: str/float (Column E) - from PR-1
            - Insurance Payment: str/float (Column F) - from Paid Amount
    
    Returns:
        Dictionary with calculated values and validation flags
    """

    # Extract values with safe conversion
    copay = safe_float(data.get("Copay"))
    deductible = safe_float(data.get("Deductible"))
    insurance_payment = safe_float(data.get("Insurance Payment"))

    # === COLUMN G: Contracted Insurance Rate ===
    # Formula: D + E + F
    # This is the total allowed amount per insurance contract
    contracted_rate = copay + deductible + insurance_payment

    # === COLUMN H: 65% Counselor Contracted Rate ===
    # This is 65% of the contracted rate (for reference)
    counselor_65_percent = contracted_rate * 0.65

    # === COLUMN I: Amount to Counselor (copay and deductible subtracted) ===
    # Formula: F - (D + E)
    # This is the ACTUAL payout after patient responsibility is removed
    # This is what the counselor actually receives
    amount_to_counselor = insurance_payment - (copay + deductible)

    # === COLUMN J: 35% GWC Share ===
    # This is 35% of the contracted rate (GWC's portion)
    gwc_35_percent = contracted_rate * 0.35

    # === Validation Checks ===
    missing_fields = []
    warnings = []
    
    # Insurance payment is required
    if not insurance_payment:
        missing_fields.append("Insurance Payment")
        warnings.append("Missing insurance payment - cannot calculate payout")
    
    # Check if payout is negative (indicates potential issue)
    if amount_to_counselor < 0:
        warnings.append(
            f"Negative payout: ${amount_to_counselor:.2f} "
            f"(Insurance ${insurance_payment:.2f} - Patient Responsibility ${copay + deductible:.2f})"
        )
    
    # Check if contracted rate seems too low
    if contracted_rate < 50 and contracted_rate > 0:
        warnings.append(
            f"Contracted rate seems low: ${contracted_rate:.2f} - verify amounts"
        )
    
    # Check if copay + deductible exceeds insurance payment (unusual but can happen)
    if (copay + deductible) > insurance_payment and insurance_payment > 0:
        warnings.append(
            f"Patient responsibility (${copay + deductible:.2f}) exceeds insurance payment (${insurance_payment:.2f})"
        )
    
    # Calculations are valid if we have an insurance payment
    calculations_valid = insurance_payment > 0

    return {
        "contracted_rate": contracted_rate,           # Column G
        "counselor_65_percent": counselor_65_percent, # Column H
        "total_payout": amount_to_counselor,          # Column I
        "gwc_35_percent": gwc_35_percent,             # Column J
        "client_responsibility": copay + deductible,   # For display
        "calculations_valid": calculations_valid,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "used_fixed_rate": False
    }


def format_currency(value: Optional[float]) -> str:
    """Format a numeric value as currency."""
    if value is None:
        return "N/A"
    try:
        return f"${value:,.2f}"
    except Exception:
        return str(value)


def get_calculation_report(
    data: Dict[str, Union[str, float]],
    results: Dict[str, Union[float, str, bool, list]]
) -> str:
    """
    Generate a human-readable calculation report for debugging.
    
    Args:
        data: Original claim data dictionary
        results: Dictionary returned from calculate_all()
    
    Returns:
        Formatted string explaining the calculations
    """
    lines = ["=== Claim Financial Summary ===", ""]
    
    # Input values
    lines.append("INPUT VALUES:")
    lines.append(f"  D - Copay (Patient Payment): {data.get('Copay', 'N/A')}")
    lines.append(f"  E - Deductible (Patient Payment): {data.get('Deductible', 'N/A')}")
    lines.append(f"  F - Insurance Payment: {data.get('Insurance Payment', 'N/A')}")
    lines.append("")
    
    # Calculation formula
    lines.append("FORMULAS:")
    lines.append("  G = D + E + F (Contracted Rate)")
    lines.append("  H = G × 0.65 (65% Counselor Share)")
    lines.append("  I = F - (D + E) (Amount to Counselor)")
    lines.append("  J = G × 0.35 (35% GWC Share)")
    lines.append("")
    
    # Calculated values
    lines.append("CALCULATED VALUES:")
    lines.append(f"  G - Contracted Insurance Rate: {format_currency(results['contracted_rate'])}")
    lines.append(f"  H - 65% Counselor Share: {format_currency(results['counselor_65_percent'])}")
    lines.append(f"  I - Amount to Counselor: {format_currency(results['total_payout'])}")
    lines.append(f"  J - 35% to GWC: {format_currency(results['gwc_35_percent'])}")
    
    # Warnings
    if results.get("warnings"):
        lines.append("")
        lines.append("⚠️  WARNINGS:")
        for warning in results["warnings"]:
            lines.append(f"    • {warning}")
    
    # Validation status
    if not results["calculations_valid"]:
        lines.append("")
        lines.append("❌ VALIDATION FAILED")
        if results["missing_fields"]:
            lines.append("    Missing: " + ", ".join(results["missing_fields"]))
    
    return "\n".join(lines)


# ============================================================================
# TEST CASES
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CALCULATIONS MODULE - TEST CASES")
    print("=" * 80)
    print()
    
    # Test Case 1: George Orwell claim (PR-3 + CO-45)
    print("TEST CASE 1: George Orwell (PR-3: $15 copay, CO-45: $192.99 write-off)")
    print("-" * 80)
    test1 = {
        "Copay": "15.00",         # PR-3: Patient copay
        "Deductible": "0",         # No deductible
        "Insurance Payment": "92.01"  # Insurance paid
        # Note: CO-45 adjustment ($192.99) is provider write-off, NOT in formula
    }
    result1 = calculate_all(test1)
    print(get_calculation_report(test1, result1))
    print()
    print(f"Expected Results:")
    print(f"  Contracted Rate: $107.01 (15 + 0 + 92.01)")
    print(f"  Amount to Counselor: $77.01 (92.01 - 15)")
    print(f"  65% Share: $69.56")
    print(f"  35% Share: $37.45")
    print()
    
    # Test Case 2: Claim with only CO code (no patient responsibility)
    print("TEST CASE 2: CO-45 Only (No patient responsibility)")
    print("-" * 80)
    test2 = {
        "Copay": "0",
        "Deductible": "0",
        "Insurance Payment": "110.20"
        # Note: CO-45 adjustment ($239.80) is provider write-off
    }
    result2 = calculate_all(test2)
    print(get_calculation_report(test2, result2))
    print()
    print(f"Expected Results:")
    print(f"  Contracted Rate: $110.20 (0 + 0 + 110.20)")
    print(f"  Amount to Counselor: $110.20 (110.20 - 0)")
    print(f"  65% Share: $71.63")
    print(f"  35% Share: $38.57")
    print()
    
    # Test Case 3: Claim with deductible (PR-1)
    print("TEST CASE 3: PR-1 Deductible")
    print("-" * 80)
    test3 = {
        "Copay": "0",
        "Deductible": "50.00",    # PR-1: Patient deductible
        "Insurance Payment": "100.00"
    }
    result3 = calculate_all(test3)
    print(get_calculation_report(test3, result3))
    print()
    print(f"Expected Results:")
    print(f"  Contracted Rate: $150.00 (0 + 50 + 100)")
    print(f"  Amount to Counselor: $50.00 (100 - 50)")
    print(f"  65% Share: $97.50")
    print(f"  35% Share: $52.50")
    print()
    
    # Test Case 4: Copay + Deductible (PR-3 + PR-1)
    print("TEST CASE 4: PR-3 Copay + PR-1 Deductible")
    print("-" * 80)
    test4 = {
        "Copay": "25.00",         # PR-3
        "Deductible": "50.00",    # PR-1
        "Insurance Payment": "125.00"
    }
    result4 = calculate_all(test4)
    print(get_calculation_report(test4, result4))
    print()
    print(f"Expected Results:")
    print(f"  Contracted Rate: $200.00 (25 + 50 + 125)")
    print(f"  Amount to Counselor: $50.00 (125 - 75)")
    print(f"  65% Share: $130.00")
    print(f"  35% Share: $70.00")
    print()
    
    print("=" * 80)
    print("END OF TEST CASES")
    print("=" * 80)