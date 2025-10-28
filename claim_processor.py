# claim_processor.py - FIXED VERSION
"""
Orchestrates the complete claim processing pipeline:
OCR → Validation → Calculation → Export to Excel/Word

CRITICAL FIX: Properly separates PR codes (patient responsibility) 
from CO codes (provider write-offs) to prevent double-counting.
"""

import os
from typing import Dict, List, Optional

# Import all processing modules
import ocr_module
import claim_validator
import calculations_module
import excel_module
import word_module
import remark_code_mapper


def process_claim(
    image_path: str,
    counselors_list: List[str],
    counselor: str = None,
    insurance: str = None,
    copay: str = None,
    deductible: str = None
) -> Dict:
    """
    Main processing function that orchestrates the entire claim workflow.
    
    Args:
        image_path: Path to ERA screenshot/PDF
        counselors_list: List of valid counselor names
        counselor: Selected counselor name (required)
        insurance: Insurance company name (optional - can override OCR)
        copay: Manual copay override (optional)
        deductible: Manual deductible override (optional)
    
    Returns:
        Dictionary with:
            - success: bool
            - message: str (error message if failed)
            - data: dict (extracted claim data)
            - calculations: dict (financial calculations)
            - validation: dict (validation results)
    """
    
    try:
        # Validate inputs
        if not counselor:
            return {
                "success": False,
                "message": "Counselor selection is required"
            }
        
        if not os.path.exists(image_path):
            return {
                "success": False,
                "message": f"Image file not found: {image_path}"
            }
        
        # ═══════════════════════════════════════════════════════════
        # STEP 1: OCR EXTRACTION
        # ═══════════════════════════════════════════════════════════
        print(f"[1/5] Running OCR on {os.path.basename(image_path)}...")
        ocr_data = ocr_module.extract_claim(image_path)
        
        if not ocr_data:
            return {
                "success": False,
                "message": "OCR extraction failed - no data returned"
            }
        
        # ═══════════════════════════════════════════════════════════
        # STEP 2: REMARK CODE PROCESSING (CRITICAL FIX)
        # ═══════════════════════════════════════════════════════════
        print("[2/5] Processing remark codes...")
        
        remarks = ocr_data.get("Remarks", "")
        patient_amount = ocr_data.get("Patient Amount", ocr_data.get("Client Responsibility", ""))
        adjustment_amount = ocr_data.get("Adjustments Amount", ocr_data.get("Adjustments", ""))
        
        # Map remark codes to financial categories
        remark_mapping = remark_code_mapper.map_remark_codes(
            remarks,
            patient_amount,
            adjustment_amount
        )
        
        # ═══════════════════════════════════════════════════════════
        # CRITICAL FIX: Separate PR codes from CO codes
        # ═══════════════════════════════════════════════════════════
        
        # Initialize with zeros
        ocr_data["Copay"] = "0"
        ocr_data["Deductible"] = "0"
        
        # Check for manual overrides FIRST
        if copay:
            ocr_data["Copay"] = copay
            print(f"   ✓ Manual copay override: ${copay}")
        elif deductible:
            ocr_data["Deductible"] = deductible
            print(f"   ✓ Manual deductible override: ${deductible}")
        else:
            # Use remark code logic ONLY if no manual overrides
            if remark_mapping.get("copay"):
                # PR-3 or PR-2: Patient Amount goes to Copay
                ocr_data["Copay"] = remark_mapping["copay"]
                print(f"   → PR-3/PR-2 found: Copay = ${remark_mapping['copay']}")
            
            elif remark_mapping.get("deductible"):
                # PR-1 or PR-140: Patient Amount goes to Deductible
                ocr_data["Deductible"] = remark_mapping["deductible"]
                print(f"   → PR-1/PR-140 found: Deductible = ${remark_mapping['deductible']}")
            
            elif remark_mapping.get("coinsurance"):
                # PR-2 (coinsurance): Goes to Copay column
                ocr_data["Copay"] = remark_mapping["coinsurance"]
                print(f"   → PR-2 (coinsurance) found: Copay = ${remark_mapping['coinsurance']}")
            
            else:
                # No PR codes found - check if there's a patient amount
                if patient_amount and patient_amount != "NOTFOUND":
                    try:
                        # Clean and parse patient amount
                        clean_amt = patient_amount.replace('$', '').replace(',', '').replace('(', '').replace(')', '').strip()
                        patient_amt = float(clean_amt)
                        
                        if patient_amt > 0:
                            # Patient amount exists but no PR code - default to copay
                            ocr_data["Copay"] = clean_amt
                            print(f"   ⚠️  Patient Amount ${patient_amt} found but NO PR code - defaulting to Copay")
                        else:
                            print(f"   ✓ Patient Amount is $0 - No copay or deductible")
                    except (ValueError, TypeError):
                        print(f"   ⚠️  Could not parse Patient Amount: {patient_amount}")
        
        # ═══════════════════════════════════════════════════════════
        # LOG PROVIDER ADJUSTMENTS (CO codes) - NOT added to patient responsibility
        # ═══════════════════════════════════════════════════════════
        if remark_mapping.get("provider_adjustment"):
            co_amount = remark_mapping["provider_adjustment"]
            print(f"   → CO code found: Provider write-off = ${co_amount}")
            print(f"      (This is NOT added to patient responsibility)")
            
            # Store for reference but don't use in calculations
            ocr_data["Provider Adjustment"] = co_amount
            ocr_data["CO Codes"] = ", ".join([c for c in remark_mapping.get("codes_found", []) if c.startswith("CO-")])
        
        # ═══════════════════════════════════════════════════════════
        # STEP 3: APPLY ADDITIONAL MANUAL OVERRIDES
        # ═══════════════════════════════════════════════════════════
        print("[3/5] Applying additional overrides...")
        
        # Override insurance if provided
        if insurance:
            ocr_data["Insurance"] = insurance
            print(f"   → Insurance override: {insurance}")
        elif "Insurance" not in ocr_data or not ocr_data["Insurance"]:
            ocr_data["Insurance"] = ""
        
        # ═══════════════════════════════════════════════════════════
        # STEP 4: VALIDATION
        # ═══════════════════════════════════════════════════════════
        print("[4/5] Validating claim data...")
        
        validation_results = claim_validator.validate_claim(ocr_data)
        
        # Log validation warnings (non-blocking)
        if validation_results.get("warnings"):
            print("\n⚠️  VALIDATION WARNINGS:")
            for warning in validation_results["warnings"]:
                print(f"   • {warning}")
        
        # ═══════════════════════════════════════════════════════════
        # STEP 5: FINANCIAL CALCULATIONS
        # ═══════════════════════════════════════════════════════════
        print("\n💰 Calculating financial breakdown...")
        
        # Print the values being used
        print(f"   Copay (D): ${ocr_data.get('Copay', 0)}")
        print(f"   Deductible (E): ${ocr_data.get('Deductible', 0)}")
        print(f"   Insurance Payment (F): ${ocr_data.get('Insurance Payment', 0)}")
        
        calculations = calculations_module.calculate_all(ocr_data)
        
        # Print calculation results
        print(f"\n   RESULTS:")
        print(f"   Contracted Rate (G) = D + E + F = ${calculations['contracted_rate']:.2f}")
        print(f"   65% Counselor Share (H) = ${calculations['counselor_65_percent']:.2f}")
        print(f"   Amount to Counselor (I) = F - (D + E) = ${calculations['total_payout']:.2f}")
        print(f"   35% GWC Share (J) = ${calculations['gwc_35_percent']:.2f}")
        
        # ═══════════════════════════════════════════════════════════
        # STEP 6: EXPORT TO EXCEL
        # ═══════════════════════════════════════════════════════════
        print(f"\n📊 Exporting to Excel: {counselor}.xlsx")
        
        excel_module.append_to_excel(
            counselor=counselor,
            data=ocr_data,
            calculations=calculations
        )
        
        # ═══════════════════════════════════════════════════════════
        # STEP 7: EXPORT TO WORD
        # ═══════════════════════════════════════════════════════════
        print(f"📄 Exporting to Word: {counselor}.docx")
        
        word_module.append_to_word(
            counselor=counselor,
            data=ocr_data,
            image_path=image_path
        )
        
        # ═══════════════════════════════════════════════════════════
        # SUCCESS - RETURN RESULTS
        # ═══════════════════════════════════════════════════════════
        print("✅ Processing complete!\n")
        
        return {
            "success": True,
            "message": "Claim processed successfully",
            "data": ocr_data,
            "calculations": calculations,
            "validation": validation_results,
            "remark_mapping": remark_mapping
        }
        
    except Exception as e:
        # Catch any unexpected errors
        import traceback
        error_details = traceback.format_exc()
        print(f"\n❌ FATAL ERROR:\n{error_details}")
        
        return {
            "success": False,
            "message": f"Processing failed: {str(e)}\n\nDetails:\n{error_details}"
        }


def batch_process_claims(
    image_paths: List[str],
    counselors_list: List[str],
    counselor: str,
    insurance: str = None,
    copay: str = None,
    deductible: str = None
) -> List[Dict]:
    """
    Process multiple claims in batch.
    
    Args:
        image_paths: List of image file paths
        counselors_list: List of valid counselor names
        counselor: Selected counselor name
        insurance: Insurance company override (optional)
        copay: Copay override (optional)
        deductible: Deductible override (optional)
    
    Returns:
        List of result dictionaries (one per claim)
    """
    
    results = []
    
    print(f"\n{'═' * 80}")
    print(f"BATCH PROCESSING: {len(image_paths)} claims")
    print(f"{'═' * 80}\n")
    
    for i, image_path in enumerate(image_paths, 1):
        print(f"\n[CLAIM {i}/{len(image_paths)}] {os.path.basename(image_path)}")
        print("─" * 80)
        
        result = process_claim(
            image_path=image_path,
            counselors_list=counselors_list,
            counselor=counselor,
            insurance=insurance,
            copay=copay,
            deductible=deductible
        )
        
        results.append(result)
        
        if result["success"]:
            print(f"✅ Claim {i} completed successfully")
        else:
            print(f"❌ Claim {i} failed: {result['message']}")
    
    print(f"\n{'═' * 80}")
    print(f"BATCH COMPLETE: {sum(1 for r in results if r['success'])}/{len(results)} successful")
    print(f"{'═' * 80}\n")
    
    return results


# ═══════════════════════════════════════════════════════════════
# STANDALONE TESTING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 24 + "CLAIM PROCESSOR TEST MODE" + " " * 29 + "║")
    print("╚" + "═" * 78 + "╝\n")
    
    if len(sys.argv) < 2:
        print("Usage: python claim_processor.py <image_path> [counselor] [insurance]")
        print("\nExample:")
        print("  python claim_processor.py claim_screenshot.png DrSmith Aetna")
        sys.exit(1)
    
    image_path = sys.argv[1]
    counselor = sys.argv[2] if len(sys.argv) > 2 else "TestCounselor"
    insurance = sys.argv[3] if len(sys.argv) > 3 else ""
    
    result = process_claim(
        image_path=image_path,
        counselors_list=[counselor],
        counselor=counselor,
        insurance=insurance
    )
    
    if result["success"]:
        print("\n✅ TEST PASSED")
        print(f"\nExtracted Data:")
        for key, value in result["data"].items():
            if not key.startswith("_"):
                print(f"  {key}: {value}")
    else:
        print(f"\n❌ TEST FAILED: {result['message']}")
        sys.exit(1)