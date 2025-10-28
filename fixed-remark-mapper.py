# remark_mapper.py - ERA Remark Code Classification for Insurance Billing
"""
Interprets ERA adjustment reason codes (PR, CO, OA, PI) and classifies
patient responsibility vs provider adjustments per standard billing rules.

UPDATED: Now handles MULTIPLE codes on same claim (e.g., PR-3 + CO-38)

References:
- PR (Patient Responsibility): Patient must pay
- CO (Contractual Obligation): Provider writes off per contract
- OA (Other Adjustments): Administrative, not patient responsibility
- PI (Payer-Initiated): Insurance plan limits, may or may not be patient responsibility
"""

from typing import Dict, Tuple, Optional
import re


def map_remark_codes(remarks: str, patient_amount: str, adjustment_amount: str = "") -> Dict[str, any]:
    """
    Parse ERA remark codes and classify financial responsibility.
    
    UPDATED: Now processes ALL codes, not just first match.
    Handles mixed scenarios like PR-3 (patient copay) + CO-38 (provider write-off).
    
    Args:
        remarks: String containing remark codes (e.g., "PR-3: Co-payment Amount CO-38: Services not provided")
        patient_amount: Dollar amount from Patient Amount column (e.g., "15.00" or "($15.00)")
        adjustment_amount: Dollar amount from Adjustments column (e.g., "50.00" or "($50.00)")
    
    Returns:
        Dictionary with:
            - copay: str (patient copay amount or "")
            - deductible: str (patient deductible amount or "")
            - coinsurance: str (patient coinsurance amount or "")
            - provider_adjustment: str (contractual write-off amount or "")
            - classification: str (human-readable category)
            - adjustment_reason: str (explanation of adjustment)
            - patient_owes: bool (True if patient must pay)
            - codes_found: list (all remark codes detected)
    """
    
    # Normalize inputs
    remarks = (remarks or "").upper().strip()
    patient_amount_clean = _clean_amount(patient_amount)
    adjustment_amount_clean = _clean_amount(adjustment_amount)
    
    # Initialize return values
    copay = ""
    deductible = ""
    coinsurance = ""
    provider_adjustment = ""
    classification_parts = []
    adjustment_reasons = []
    patient_owes = False
    codes_found = []
    
    # Extract all remark codes from text
    all_codes = re.findall(r'\b(PR|CO|OA|PI)-?(\d+)\b', remarks)
    codes_found = [f"{code}-{num}" for code, num in all_codes]
    
    # === PROCESS PR CODES (Patient Responsibility) ===
    pr_codes = [num for code, num in all_codes if code == "PR"]
    
    for pr_num in pr_codes:
        if pr_num in ["3", "03"]:
            # PR-3: Copayment Amount
            if not copay:  # Only set if not already set
                copay = patient_amount_clean
            classification_parts.append("Copay")
            adjustment_reasons.append("Patient copayment per insurance plan")
            patient_owes = True
        
        elif pr_num in ["1", "01"]:
            # PR-1: Deductible Amount
            if not deductible:
                deductible = patient_amount_clean
            classification_parts.append("Deductible")
            adjustment_reasons.append("Patient deductible not met")
            patient_owes = True
        
        elif pr_num in ["2", "02"]:
            # PR-2: Coinsurance Amount
            if not coinsurance:
                coinsurance = patient_amount_clean
            classification_parts.append("Coinsurance")
            adjustment_reasons.append("Patient coinsurance per plan percentage")
            patient_owes = True
        
        elif pr_num == "140":
            # PR-140: Patient/Insured health identification mismatch (DENIAL)
            if not deductible:
                deductible = patient_amount_clean
            classification_parts.append("Denial - Patient ID Mismatch")
            adjustment_reasons.append("Claim denied: Patient identification does not match insurance records")
            patient_owes = True
        
        else:
            # Other PR codes: Generic patient responsibility
            if not copay and not deductible:
                copay = patient_amount_clean
            classification_parts.append("Patient Responsibility (Other)")
            adjustment_reasons.append(f"Patient responsibility per insurance determination (PR-{pr_num})")
            patient_owes = True
    
    # === PROCESS CO CODES (Contractual Obligation - Provider Write-Off) ===
    co_codes = [num for code, num in all_codes if code == "CO"]
    
    if co_codes:
        # Use adjustment_amount if provided, otherwise fall back to patient_amount
        adj_amount = adjustment_amount_clean if adjustment_amount_clean else patient_amount_clean
        
        for co_num in co_codes:
            if co_num == "38":
                # CO-38: Out of network services
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Contractual Adjustment - Out of Network")
                adjustment_reasons.append("Provider contractual write-off: Out of network services")
            
            elif co_num == "11":
                # CO-11: Service not covered
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Contractual Adjustment - Not Covered")
                adjustment_reasons.append("Provider write-off: Service not covered under plan")
            
            elif co_num == "16":
                # CO-16: Incomplete information
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Contractual Adjustment - Incomplete Info")
                adjustment_reasons.append("Provider write-off: Claim lacks required information")
            
            elif co_num == "97":
                # CO-97: Bundled service
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Contractual Adjustment - Bundled")
                adjustment_reasons.append("Provider write-off: Service bundled with another procedure")
            
            else:
                # Other CO codes
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Contractual Adjustment")
                adjustment_reasons.append(f"Provider contractual write-off per insurance agreement (CO-{co_num})")
    
    # === PROCESS OA CODES (Other Adjustments) ===
    oa_codes = [num for code, num in all_codes if code == "OA"]
    
    if oa_codes:
        adj_amount = adjustment_amount_clean if adjustment_amount_clean else patient_amount_clean
        
        for oa_num in oa_codes:
            if oa_num == "18":
                # OA-18: Duplicate claim
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Administrative Adjustment - Duplicate")
                adjustment_reasons.append("Administrative adjustment: Duplicate claim")
            
            elif oa_num == "23":
                # OA-23: Administrative error
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Administrative Adjustment - Error")
                adjustment_reasons.append("Administrative adjustment: Payer error correction")
            
            else:
                # Other OA codes
                if not provider_adjustment:
                    provider_adjustment = adj_amount
                classification_parts.append("Administrative Adjustment")
                adjustment_reasons.append(f"Administrative adjustment by payer (OA-{oa_num})")
    
    # === PROCESS PI CODES (Payer-Initiated Reductions) ===
    pi_codes = [num for code, num in all_codes if code == "PI"]
    
    for pi_num in pi_codes:
        if pi_num == "204":
            # PI-204: Service not covered
            if not copay and not deductible:
                copay = patient_amount_clean
            classification_parts.append("Payer-Initiated - Not Covered")
            adjustment_reasons.append("Service not covered: Patient may be responsible or provider may write off")
            patient_owes = True
        
        elif pi_num == "119":
            # PI-119: Benefit maximum exceeded
            if not copay and not deductible:
                copay = patient_amount_clean
            classification_parts.append("Payer-Initiated - Benefit Max Exceeded")
            adjustment_reasons.append("Benefit maximum reached: Patient may be responsible")
            patient_owes = True
        
        else:
            # Other PI codes
            if not copay and not deductible:
                copay = patient_amount_clean
            classification_parts.append("Payer-Initiated Reduction")
            adjustment_reasons.append(f"Payer-initiated adjustment: Review required (PI-{pi_num})")
            patient_owes = True
    
    # === HANDLE NO CODES FOUND ===
    if not codes_found:
        if patient_amount_clean:
            copay = patient_amount_clean
            classification_parts.append("Unclassified Patient Amount")
            adjustment_reasons.append("No remark code found - manual review recommended")
            patient_owes = True
    
    # === BUILD FINAL CLASSIFICATION STRING ===
    if classification_parts:
        classification = " + ".join(classification_parts)
    else:
        classification = "Unknown"
    
    adjustment_reason = " | ".join(adjustment_reasons) if adjustment_reasons else ""
    
    return {
        "copay": copay,
        "deductible": deductible,
        "coinsurance": coinsurance,
        "provider_adjustment": provider_adjustment,
        "classification": classification,
        "adjustment_reason": adjustment_reason,
        "patient_owes": patient_owes,
        "codes_found": codes_found  # NEW: List of all codes detected
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
    if not amount or amount in ("NOTFOUND", "N/A", ""):
        return ""
    
    # Remove $, commas, parentheses, and whitespace
    cleaned = amount.replace("$", "").replace(",", "").replace("(", "").replace(")", "").strip()
    
    # Validate it's a number
    try:
        float(cleaned)
        return cleaned
    except (ValueError, TypeError):
        return ""


def get_remark_code_report(mapping_result: Dict) -> str:
    """
    Generate human-readable report of remark code classification.
    
    Args:
        mapping_result: Dictionary returned from map_remark_codes()
    
    Returns:
        Formatted string explaining the classification
    """
    lines = ["=== ERA Remark Code Analysis ===", ""]
    
    # Show all codes found
    if mapping_result.get('codes_found'):
        lines.append(f"Codes Found: {', '.join(mapping_result['codes_found'])}")
        lines.append("")
    
    lines.append(f"Classification: {mapping_result['classification']}")
    lines.append(f"Reason: {mapping_result['adjustment_reason']}")
    lines.append(f"Patient Owes: {'Yes' if mapping_result['patient_owes'] else 'No'}")
    lines.append("")
    
    if mapping_result['copay']:
        lines.append(f"Copay: ${mapping_result['copay']}")
    if mapping_result['deductible']:
        lines.append(f"Deductible: ${mapping_result['deductible']}")
    if mapping_result['coinsurance']:
        lines.append(f"Coinsurance: ${mapping_result['coinsurance']}")
    if mapping_result['provider_adjustment']:
        lines.append(f"Provider Adjustment (Write-Off): ${mapping_result['provider_adjustment']}")
    
    return "\n".join(lines)
