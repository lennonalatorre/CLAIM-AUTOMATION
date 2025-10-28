#!/usr/bin/env python3
"""
Insurance Claim Validator - Standalone OCR Data Rules Checker
==============================================================
Validates OCR-extracted claim data against insurance billing rules.
Standard library only. No auto-filling - only flags issues.

Author: Insurance Biller Automation Team
"""

from typing import Dict, List, Tuple, Optional, Any

# Tolerance for floating-point comparison
EPS = 0.01


def safe_float(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Safely parse a value to float, handling common OCR formats.
    
    Accepts: numbers, "$1,234.56", "1234.56", etc.
    Rejects: "NOTFOUND", None, empty strings, non-numeric text
    
    Args:
        value: Any value from OCR data (str, int, float, None)
    
    Returns:
        Tuple of (parsed_float or None, warning_message or None)
    
    Examples:
        safe_float("$1,234.56") -> (1234.56, None)
        safe_float("NOTFOUND") -> (None, "Invalid value: NOTFOUND")
        safe_float(125.0) -> (125.0, None)
    """
    # Handle None, empty, or placeholder values
    if value is None or value == "" or value == "NOTFOUND" or value == "N/A":
        return None, None
    
    # Already a number
    if isinstance(value, (int, float)):
        return float(value), None
    
    # String conversion
    if isinstance(value, str):
        # Remove common currency formatting
        cleaned = value.strip().replace("$", "").replace(",", "").replace("(", "").replace(")", "")
        
        if not cleaned:
            return None, None
        
        try:
            return float(cleaned), None
        except ValueError:
            return None, f"Invalid numeric value: {value}"
    
    # Unexpected type
    return None, f"Unexpected value type: {type(value).__name__}"


def normalize_numeric_fields(data: Dict[str, Any]) -> Tuple[Dict[str, Optional[float]], List[str]]:
    """
    Extract and normalize all numeric fields from OCR data.
    
    Insurance billing rule: All dollar amounts must be parseable numbers.
    Missing values are acceptable (will be None), but invalid strings are flagged.
    
    Args:
        data: Dictionary with OCR-extracted claim data
    
    Returns:
        Tuple of (normalized_dict, warnings_list)
        - normalized_dict: Keys are field names, values are floats or None
        - warnings_list: Human-readable warnings for parsing issues
    """
    warnings = []
    normalized = {}
    
    # Required numeric fields
    required_fields = [
        "Copay",
        "Deductible", 
        "Insurance Payment",
        "Contracted Rate",
        "Paid Amount"
    ]
    
    # Optional numeric fields
    optional_fields = [
        "Patient Amount",
        "Adjustments Amount"
    ]
    
    all_fields = required_fields + optional_fields
    
    for field in all_fields:
        value = data.get(field)
        parsed, warning = safe_float(value)
        
        # Store normalized value (may be None)
        normalized[field.lower().replace(" ", "_")] = parsed
        
        # Flag parsing errors (but not missing values for optional fields)
        if warning and field in required_fields:
            warnings.append(f"{field}: {warning}")
        elif warning and field in optional_fields and value is not None:
            warnings.append(f"{field}: {warning}")
    
    return normalized, warnings


def check_financial_logic(nums: Dict[str, Optional[float]]) -> Tuple[Optional[float], List[str], Optional[bool]]:
    """
    Validate financial calculations per insurance billing rules.
    
    Rules:
    1. Contracted Rate = Copay + Deductible + Insurance Payment
       (This is the allowed amount negotiated with the insurance company)
    
    2. Counselor Payout = Insurance Payment - (Copay + Deductible)
       (This is what the counselor actually receives after patient responsibility)
    
    3. All amounts should be >= 0 (except counselor payout can be negative on denials)
    
    Args:
        nums: Normalized numeric fields from normalize_numeric_fields()
    
    Returns:
        Tuple of (counselor_payout, warnings, contracted_rate_ok)
    """
    warnings = []
    counselor_payout = None
    contracted_rate_ok = None
    
    # Extract values (may be None)
    copay = nums.get("copay", 0) or 0
    deductible = nums.get("deductible", 0) or 0
    insurance_payment = nums.get("insurance_payment", 0) or 0
    contracted_rate = nums.get("contracted_rate")
    paid_amount = nums.get("paid_amount")
    
    # Rule: Insurance Payment should equal Paid Amount (if both present)
    if insurance_payment and paid_amount and abs(insurance_payment - paid_amount) > EPS:
        warnings.append(
            f"Insurance Payment (${insurance_payment:.2f}) does not match "
            f"Paid Amount (${paid_amount:.2f})"
        )
    
    # Rule: Negative amounts are suspicious (except on denials)
    if copay < 0:
        warnings.append(f"Copay is negative: ${copay:.2f}")
    if deductible < 0:
        warnings.append(f"Deductible is negative: ${deductible:.2f}")
    if insurance_payment < 0:
        warnings.append(f"Insurance Payment is negative: ${insurance_payment:.2f}")
    
    # Rule: Contracted Rate must equal Copay + Deductible + Insurance Payment
    if contracted_rate is not None:
        expected_contracted = copay + deductible + insurance_payment
        
        if abs(contracted_rate - expected_contracted) > EPS:
            warnings.append(
                f"Contracted Rate (${contracted_rate:.2f}) does not equal "
                f"Copay + Deductible + Insurance Payment (${expected_contracted:.2f})"
            )
            contracted_rate_ok = False
        else:
            contracted_rate_ok = True
    else:
        warnings.append("Contracted Rate is missing")
        contracted_rate_ok = None
    
    # Rule: Calculate counselor payout
    # Insurance billing: Counselor receives insurance payment minus patient responsibility
    if insurance_payment is not None:
        counselor_payout = insurance_payment - (copay + deductible)
        
        # Flag negative payouts (may be legitimate on denials, but worth reviewing)
        if counselor_payout < -EPS:
            warnings.append(
                f"Counselor Payout is negative: ${counselor_payout:.2f} "
                f"(Insurance Payment ${insurance_payment:.2f} - "
                f"Patient Responsibility ${copay + deductible:.2f})"
            )
    else:
        warnings.append("Cannot calculate Counselor Payout: Insurance Payment missing")
    
    return counselor_payout, warnings, contracted_rate_ok


def check_remarks_logic(data: Dict[str, Any], nums: Dict[str, Optional[float]]) -> List[str]:
    """
    Validate remark codes against patient responsibility amounts.
    
    Insurance billing rules for remark codes:
    - PR-1 = Deductible responsibility → Deductible must be nonzero
    - PR-2 = Coinsurance responsibility → Some patient amount must be nonzero
    - PR-3 = Copay responsibility → Copay must be nonzero
    - CO-xx = Contractual adjustment → Provider writes off, patient owes nothing
    - OA/PI = Other adjustments → Context-dependent
    
    Critical rule: Codes indicate TYPE of responsibility, not amounts.
    We flag inconsistencies but never auto-fill values.
    
    Args:
        data: Original OCR data (for Remarks field)
        nums: Normalized numeric fields
    
    Returns:
        List of warning strings
    """
    warnings = []
    
    # Extract remarks (may be list or string)
    remarks = data.get("Remarks", [])
    if isinstance(remarks, str):
        remarks = [remarks]
    elif not isinstance(remarks, list):
        remarks = []
    
    # Normalize remarks to uppercase for comparison
    remarks_upper = [str(r).upper().strip() for r in remarks]
    
    # Extract patient responsibility amounts
    copay = nums.get("copay", 0) or 0
    deductible = nums.get("deductible", 0) or 0
    
    # Detect code types
    has_pr1 = any("PR-1" in r or "PR-01" in r for r in remarks_upper)
    has_pr2 = any("PR-2" in r or "PR-02" in r for r in remarks_upper)
    has_pr3 = any("PR-3" in r or "PR-03" in r for r in remarks_upper)
    has_any_pr = any(r.startswith("PR-") for r in remarks_upper)
    has_only_co = all(r.startswith("CO-") for r in remarks_upper) and len(remarks_upper) > 0
    has_any_co = any(r.startswith("CO-") for r in remarks_upper)
    
    # Rule: PR-1 requires nonzero deductible
    if has_pr1 and abs(deductible) < EPS:
        warnings.append(
            "PR-1 (Deductible) present but Deductible is missing or zero"
        )
    
    # Rule: PR-2 (coinsurance) requires some patient responsibility
    if has_pr2 and abs(copay) < EPS and abs(deductible) < EPS:
        warnings.append(
            "PR-2 (Coinsurance) present but both Copay and Deductible are zero"
        )
    
    # Rule: PR-3 requires nonzero copay
    if has_pr3 and abs(copay) < EPS:
        warnings.append(
            "PR-3 (Copay) present but Copay is missing or zero"
        )
    
    # Rule: Any PR code should have corresponding patient responsibility
    if has_any_pr and abs(copay) < EPS and abs(deductible) < EPS:
        warnings.append(
            "Patient Responsibility (PR) codes present but both Copay and Deductible are zero"
        )
    
    # Rule: Only CO codes means patient should owe nothing
    # CO codes are contractual adjustments - provider writes off, not patient responsibility
    if has_only_co:
        if abs(copay) > EPS or abs(deductible) > EPS:
            warnings.append(
                "Only CO (Contractual Obligation) codes present, "
                "but patient responsibility amounts are nonzero. "
                "Patient should not be charged for contractual adjustments."
            )
    
    # Rule: OA/PI codes with patient amounts but no PR codes is unclear
    has_oa_or_pi = any(r.startswith("OA-") or r.startswith("PI-") for r in remarks_upper)
    if has_oa_or_pi and not has_any_pr and (abs(copay) > EPS or abs(deductible) > EPS):
        warnings.append(
            "OA/PI codes present with patient amounts but no PR codes. "
            "Patient responsibility is unclear - verify if patient should be charged."
        )
    
    return warnings


def validate_claim(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main validator: orchestrates all checks and returns structured results.
    
    This is the public API function that integrates with the claim processor.
    
    Args:
        data: OCR-extracted claim data dictionary
    
    Returns:
        Dictionary with structure:
        {
            "warnings": [list of human-readable warning strings],
            "computed": {
                "contracted_rate_check": True/False/None,
                "counselor_payout": float or None,
                "normalized": {dict of parsed numeric fields}
            }
        }
    """
    all_warnings = []
    
    # Step 1: Normalize numeric fields
    normalized, norm_warnings = normalize_numeric_fields(data)
    all_warnings.extend(norm_warnings)
    
    # Step 2: Check financial logic
    counselor_payout, finance_warnings, contracted_ok = check_financial_logic(normalized)
    all_warnings.extend(finance_warnings)
    
    # Step 3: Check remark code logic
    remark_warnings = check_remarks_logic(data, normalized)
    all_warnings.extend(remark_warnings)
    
    return {
        "warnings": all_warnings,
        "computed": {
            "contracted_rate_check": contracted_ok,
            "counselor_payout": counselor_payout,
            "normalized": normalized
        }
    }


# ============================================================================
# DEMONSTRATION / TEST CASES
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("INSURANCE CLAIM VALIDATOR - TEST CASES")
    print("=" * 80)
    print()
    
    # Test Case 1: Happy Path
    print("TEST CASE 1: Happy Path (No Issues)")
    print("-" * 80)
    test1 = {
        "Copay": 25.00,
        "Deductible": 50.00,
        "Insurance Payment": 125.00,
        "Contracted Rate": 200.00,
        "Paid Amount": 125.00,
        "Remarks": ["PR-1", "PR-3"]
    }
    result1 = validate_claim(test1)
    print(f"Input: {test1}")
    print(f"\nWarnings: {result1['warnings'] if result1['warnings'] else 'None ✓'}")
    print(f"Contracted Rate Check: {result1['computed']['contracted_rate_check']}")
    print(f"Counselor Payout: ${result1['computed']['counselor_payout']:.2f}")
    print(f"Normalized Values: {result1['computed']['normalized']}")
    print()
    
    # Test Case 2: PR-3 but Copay Missing
    print("TEST CASE 2: PR-3 Present but Copay Missing/Zero")
    print("-" * 80)
    test2 = {
        "Copay": 0,
        "Deductible": 50.00,
        "Insurance Payment": 150.00,
        "Contracted Rate": 200.00,
        "Paid Amount": 150.00,
        "Remarks": ["PR-3"]  # Claims copay but copay is 0
    }
    result2 = validate_claim(test2)
    print(f"Input: {test2}")
    print(f"\nWarnings:")
    for w in result2['warnings']:
        print(f"  ⚠️  {w}")
    print(f"Counselor Payout: ${result2['computed']['counselor_payout']:.2f}")
    print()
    
    # Test Case 3: Only CO Codes but Patient Amounts Nonzero
    print("TEST CASE 3: Only CO Codes but Patient Responsibility Nonzero")
    print("-" * 80)
    test3 = {
        "Copay": 25.00,  # Shouldn't exist with only CO codes
        "Deductible": 0,
        "Insurance Payment": 175.00,
        "Contracted Rate": 200.00,
        "Paid Amount": 175.00,
        "Remarks": ["CO-45"]  # Contractual adjustment only
    }
    result3 = validate_claim(test3)
    print(f"Input: {test3}")
    print(f"\nWarnings:")
    for w in result3['warnings']:
        print(f"  ⚠️  {w}")
    print(f"Counselor Payout: ${result3['computed']['counselor_payout']:.2f}")
    print()
    
    # Test Case 4: Math Error (Contracted Rate Mismatch)
    print("TEST CASE 4: Contracted Rate Math Mismatch")
    print("-" * 80)
    test4 = {
        "Copay": 25.00,
        "Deductible": 50.00,
        "Insurance Payment": 120.00,  # Total = 195
        "Contracted Rate": 200.00,     # But says 200 (off by $5)
        "Paid Amount": 120.00,
        "Remarks": ["PR-1", "PR-3"]
    }
    result4 = validate_claim(test4)
    print(f"Input: {test4}")
    print(f"\nWarnings:")
    for w in result4['warnings']:
        print(f"  ⚠️  {w}")
    print(f"Contracted Rate Check: {result4['computed']['contracted_rate_check']}")
    print(f"Counselor Payout: ${result4['computed']['counselor_payout']:.2f}")
    print()
    
    # Test Case 5: Negative Payout (Denial Scenario)
    print("TEST CASE 5: Negative Payout (Denial Scenario)")
    print("-" * 80)
    test5 = {
        "Copay": 0,
        "Deductible": 300.00,  # Patient owes full amount
        "Insurance Payment": 0,  # Insurance paid nothing
        "Contracted Rate": 300.00,
        "Paid Amount": 0,
        "Remarks": ["PR-140"]  # Denial code
    }
    result5 = validate_claim(test5)
    print(f"Input: {test5}")
    print(f"\nWarnings:")
    for w in result5['warnings']:
        print(f"  ⚠️  {w}")
    print(f"Counselor Payout: ${result5['computed']['counselor_payout']:.2f}")
    print()
    
    # Test Case 6: String Formatting with OCR Artifacts
    print("TEST CASE 6: OCR String Formatting (Currency Symbols, Commas)")
    print("-" * 80)
    test6 = {
        "Copay": "$25.00",
        "Deductible": "50",
        "Insurance Payment": "1,250.00",
        "Contracted Rate": "$1,325.00",
        "Paid Amount": "1250.00",
        "Remarks": ["PR-3"]
    }
    result6 = validate_claim(test6)
    print(f"Input: {test6}")
    print(f"\nWarnings: {result6['warnings'] if result6['warnings'] else 'None ✓'}")
    print(f"Counselor Payout: ${result6['computed']['counselor_payout']:.2f}")
    print(f"Normalized Values: {result6['computed']['normalized']}")
    print()
    
    print("=" * 80)
    print("END OF TEST CASES")
    print("=" * 80)
