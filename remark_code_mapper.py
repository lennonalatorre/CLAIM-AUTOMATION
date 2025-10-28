# remark_code_mapper.py - FIXED VERSION
"""
Correctly interprets ERA adjustment reason codes (PR, CO, OA, PI).

CRITICAL FIX: Now properly handles cases where BOTH PR and CO codes exist
on the same claim (e.g., PR-3: $15.00 copay + CO-38: $192.99 write-off)

KEY RULES:
- PR codes → Patient Amount column → Patient owes money
- CO codes → Adjustments Amount column → Provider write-off (patient owes $0)
- When BOTH exist, Patient Amount goes to copay/deductible, Adjustments goes to provider write-off
"""

from typing import Dict, Optional
import re


def map_remark_codes(remarks: str, patient_amount: str, adjustment_amount: str = "") -> Dict:
    """
    Parse ERA remark codes and classify financial responsibility.
    
    CRITICAL FIX: Now handles mixed PR+CO scenarios correctly.
    
    Args:
        remarks: String containing remark codes (e.g., "PR-3: Co-payment Amount CO-38: Services not provided")
        patient_amount: Dollar amount from Patient Amount column
        adjustment_amount: Dollar amount from Adjustments column
    
    Returns:
        Dictionary with:
            - copay: str (patient copay or "")
            - deductible: str (patient deductible or "")
            - coinsurance: str (patient coinsurance or "")
            - provider_adjustment: str (contractual write-off or "")
            - classification: str (human-readable category)
            - patient_owes: bool (True if patient must pay)
            - codes_found: list (all remark codes detected)
    """
    
    # Normalize inputs
    remarks = (remarks or "").upper().strip()
    patient_clean = _clean_amount(patient_amount)
    adjustment_clean = _clean_amount(adjustment_amount)
    
    # Initialize return values
    copay = ""
    deductible = ""
    coinsurance = ""
    provider_adjustment = ""
    classification = []
    patient_owes = False
    
    # Extract all remark codes
    all_codes = re.findall(r'\b(PR|CO|OA|PI)-?(\d+)\b', remarks)
    codes_found = [f"{code}-{num}" for code, num in all_codes]
    
    # Separate PR and CO codes
    pr_codes = [num for code, num in all_codes if code == "PR"]
    co_codes = [num for code, num in all_codes if code == "CO"]
    oa_codes = [num for code, num in all_codes if code == "OA"]
    pi_codes = [num for code, num in all_codes if code == "PI"]
    
    # === CRITICAL FIX: Handle PR codes FIRST (they use Patient Amount) ===
    if pr_codes:
        patient_owes = True
        
        for pr_num in pr_codes:
            if pr_num in ["3", "03"]:
                # PR-3: Copayment - uses Patient Amount
                if patient_clean:
                    copay = patient_clean
                    classification.append("Copay (PR-3)")
            
            elif pr_num in ["1", "01"]:
                # PR-1: Deductible - uses Patient Amount
                if patient_clean:
                    deductible = patient_clean
                    classification.append("Deductible (PR-1)")
            
            elif pr_num in ["2", "02"]:
                # PR-2: Coinsurance - uses Patient Amount
                if patient_clean:
                    coinsurance = patient_clean
                    classification.append("Coinsurance (PR-2)")
            
            elif pr_num == "140":
                # PR-140: Denial - patient responsible for full amount (goes to deductible)
                if patient_clean:
                    deductible = patient_clean
                    classification.append("Denial (PR-140)")
            
            else:
                # Other PR codes - uses Patient Amount
                if patient_clean and not copay and not deductible:
                    copay = patient_clean
                    classification.append(f"Patient Responsibility (PR-{pr_num})")
    
    # === CRITICAL FIX: Handle CO codes SEPARATELY (they use Adjustments Amount) ===
    if co_codes:
        # CO adjustments ALWAYS use Adjustments Amount, NOT Patient Amount
        if adjustment_clean:
            provider_adjustment = adjustment_clean
            
            for co_num in co_codes:
                if co_num == "45":
                    classification.append("Provider Write-Off (CO-45)")
                elif co_num == "38":
                    classification.append("Provider Write-Off (CO-38)")
                elif co_num == "11":
                    classification.append("Provider Write-Off (CO-11)")
                else:
                    classification.append(f"Provider Write-Off (CO-{co_num})")
        else:
            # Edge case: CO code exists but no adjustment amount found
            classification.append("Provider Write-Off (CO - amount missing)")
    
    # === Handle OA codes (Other Adjustments) ===
    if oa_codes:
        # OA codes are administrative, not patient responsibility
        if adjustment_clean and not provider_adjustment:
            provider_adjustment = adjustment_clean
        classification.append("Administrative Adjustment (OA)")
    
    # === Handle PI codes (Payer-Initiated) ===
    if pi_codes:
        # PI codes may or may not be patient responsibility
        # If there's a patient amount and no PR codes, patient may owe
        if not pr_codes and patient_clean:
            copay = patient_clean
            patient_owes = True
            classification.append("Payer-Initiated Reduction (PI)")
    
    # === Handle NO CODES FOUND ===
    if not codes_found:
        if patient_clean:
            copay = patient_clean
            patient_owes = True
            classification.append("Unclassified Patient Amount")
        if adjustment_clean:
            provider_adjustment = adjustment_clean
            classification.append("Unclassified Adjustment")
    
    # Build final classification string
    classification_str = " + ".join(classification) if classification else "No Adjustments"
    
    return {
        "copay": copay,
        "deductible": deductible,
        "coinsurance": coinsurance,
        "provider_adjustment": provider_adjustment,
        "classification": classification_str,
        "patient_owes": patient_owes,
        "codes_found": codes_found
    }


def _clean_amount(amount: str) -> str:
    """
    Clean dollar amount from ERA format.
    Removes $, commas, parentheses, and whitespace.
    
    Examples:
        "($15.00)" -> "15.00"
        "$300.00" -> "300.00"
        "(50.00)" -> "50.00"
    
    Returns empty string if amount is invalid or "NOTFOUND".
    """
    if not amount or amount in ("NOTFOUND", "N/A", "", "0", "$0", "$0.00"):
        return ""
    
    # Remove $, commas, parentheses, and whitespace
    cleaned = amount.replace("$", "").replace(",", "").replace("(", "").replace(")", "").strip()
    
    # Validate it's a number
    try:
        value = float(cleaned)
        # Return empty string for zero values
        return cleaned if value > 0 else ""
    except (ValueError, TypeError):
        return ""


def get_remark_code_report(mapping_result: Dict) -> str:
    """Generate human-readable report of remark code classification."""
    lines = ["=== ERA Remark Code Analysis ===", ""]
    
    if mapping_result.get('codes_found'):
        lines.append(f"Codes Found: {', '.join(mapping_result['codes_found'])}")
        lines.append("")
    
    lines.append(f"Classification: {mapping_result['classification']}")
    lines.append(f"Patient Owes: {'Yes' if mapping_result['patient_owes'] else 'No'}")
    lines.append("")
    
    if mapping_result['copay']:
        lines.append(f"  Copay: ${mapping_result['copay']}")
    if mapping_result['deductible']:
        lines.append(f"  Deductible: ${mapping_result['deductible']}")
    if mapping_result['coinsurance']:
        lines.append(f"  Coinsurance: ${mapping_result['coinsurance']}")
    if mapping_result['provider_adjustment']:
        lines.append(f"  Provider Adjustment (Write-Off): ${mapping_result['provider_adjustment']}")
    
    return "\n".join(lines)


# === TEST CASES ===
if __name__ == "__main__":
    print("=" * 80)
    print("REMARK CODE MAPPER - TEST CASES (FIXED VERSION)")
    print("=" * 80)
    print()
    
    # Test Case 1: Image 1 - John Doe (PR-3 + CO-38)
    print("TEST 1: John Doe - PR-3 ($15 copay) + CO-38 ($50 write-off)")
    print("-" * 80)
    result1 = map_remark_codes(
        remarks="PR-3: Co-payment Amount CO-38: Services not provided",
        patient_amount="($15.00)",
        adjustment_amount="($50.00)"
    )
    print(get_remark_code_report(result1))
    print(f"\nExpected: Copay=$15, Provider Adjustment=$50")
    print(f"Got: Copay=${result1['copay']}, Provider Adjustment=${result1['provider_adjustment']}")
    print(f"✅ PASS" if result1['copay'] == "15.00" and result1['provider_adjustment'] == "50.00" else "❌ FAIL")
    print()
    
    # Test Case 2: Image 2 - George Orwell (PR-3 + CO-45)
    print("TEST 2: George Orwell - PR-3 ($15 copay) + CO-45 ($192.99 write-off)")
    print("-" * 80)
    result2 = map_remark_codes(
        remarks="PR-3: Co-payment Amount CO-45: Charge exceeds fee schedule",
        patient_amount="($15.00)",
        adjustment_amount="($192.99)"
    )
    print(get_remark_code_report(result2))
    print(f"\nExpected: Copay=$15, Provider Adjustment=$192.99")
    print(f"Got: Copay=${result2['copay']}, Provider Adjustment=${result2['provider_adjustment']}")
    print(f"✅ PASS" if result2['copay'] == "15.00" and result2['provider_adjustment'] == "192.99" else "❌ FAIL")
    print()
    
    # Test Case 3: Image 3 - CO-45 only (no patient responsibility)
    print("TEST 3: CO-45 Only - $239.80 write-off, $0 patient")
    print("-" * 80)
    result3 = map_remark_codes(
        remarks="CO-45: Charge exceeds fee schedule",
        patient_amount="$0.00",
        adjustment_amount="($239.80)"
    )
    print(get_remark_code_report(result3))
    print(f"\nExpected: Copay=$0, Provider Adjustment=$239.80")
    print(f"Got: Copay=${result3['copay']}, Provider Adjustment=${result3['provider_adjustment']}")
    print(f"✅ PASS" if result3['copay'] == "" and result3['provider_adjustment'] == "239.80" else "❌ FAIL")
    print()
    
    print("=" * 80)
    print("END OF TESTS")
    print("=" * 80)