"""
llm_validator.py - LLM-powered validation for insurance claim OCR (FIXED v2)
============================================================================
Uses Ollama (llama3.2:3b) to enhance patient name extraction and
validate OCR results from ERA screenshots.

CRITICAL FIX v2: Improved prompt to handle OCR artifacts like:
- Dots between names (George.Orwell)
- Underscores (John_Doe)
- Garbled text (cen) rastf tite)

Author: Insurance Claim Automation Team
Version: 2.0 - Improved OCR Artifact Handling
"""

import logging
import json
import re
from typing import Dict, Optional, Tuple
import subprocess
import time

logger = logging.getLogger(__name__)


def is_ollama_available() -> bool:
    """
    Check if Ollama service is running and accessible.
    
    Returns:
        bool: True if Ollama is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='ignore'  # Handle Unicode errors gracefully
        )
        
        # Check if llama3.2:3b is in the list
        if "llama3.2:3b" in result.stdout or "llama3.2" in result.stdout:
            logger.info("✅ Ollama is available with llama3.2:3b model")
            return True
        else:
            logger.warning("⚠️  Ollama is running but llama3.2:3b not found")
            return False
            
    except FileNotFoundError:
        logger.warning("⚠️  Ollama not installed")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("⚠️  Ollama service not responding")
        return False
    except Exception as e:
        logger.warning(f"⚠️  Could not check Ollama: {e}")
        return False


def extract_patient_name(raw_text: str, ocr_name: str = "NOTFOUND") -> Optional[str]:
    """
    Extract patient name from ERA text using LLM.
    
    This is the primary use case - fixing patient name extraction
    when Tesseract fails on low-contrast or unclear text.
    
    CRITICAL FIX v2: Improved prompt to handle OCR artifacts like dots and underscores.
    
    Args:
        raw_text: Complete OCR text from ERA image
        ocr_name: What Tesseract extracted (may be "NOTFOUND")
    
    Returns:
        Extracted patient name or None if extraction fails
    """
    
    if not is_ollama_available():
        logger.info("LLM not available, skipping name extraction")
        return None
    
    # If OCR already found a valid name, no need for LLM
    if ocr_name and ocr_name != "NOTFOUND" and len(ocr_name.split()) >= 2:
        logger.info(f"OCR name looks valid: {ocr_name}, skipping LLM")
        return ocr_name
    
    logger.info("🤖 Using LLM to extract patient name...")
    start_time = time.time()
    
    # CRITICAL FIX v2: Improved prompt with explicit OCR artifact handling
    prompt = f"""You are a medical billing data extractor. Extract the patient's full name from this ERA insurance document.

CRITICAL RULES:
1. Return ONLY the patient's name in format: "FirstName LastName"
2. Remove OCR errors like dots, underscores, or special characters between words
3. Fix common OCR mistakes (e.g., "George.Orwell" → "George Orwell")
4. Do NOT include explanations, patient IDs, claim numbers, or extra text
5. If no valid patient name found, return exactly: "NOTFOUND"

EXAMPLES OF CORRECT EXTRACTION:
- Input: "Patient. George.Orwell" → Output: "George Orwell"
- Input: "Patient: John_Doe - 12345" → Output: "John Doe"
- Input: "Patient: LLOYD DOBLER - ZAQ123456789" → Output: "Lloyd Dobler"
- Input: "cen) rastf tite. + ited" → Output: "NOTFOUND"

ERA TEXT:
{raw_text[:1000]}

EXTRACT PATIENT NAME (FirstName LastName only):"""

    try:
        # Call Ollama with Unicode error handling
        result = subprocess.run(
            ["ollama", "run", "llama3.2:3b", prompt],
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
            encoding='utf-8',
            errors='ignore'  # CRITICAL: Handle Unicode decode errors
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            # Extract name from response
            response = result.stdout.strip()
            name = _parse_name_from_response(response)
            
            if name and name != "NOTFOUND":
                logger.info(f"✅ LLM extracted name: '{name}' (took {elapsed:.1f}s)")
                return name
            else:
                logger.warning(f"⚠️  LLM could not find patient name (took {elapsed:.1f}s)")
                return None
        else:
            logger.error(f"❌ Ollama error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("❌ LLM timeout (>30s) - skipping")
        return None
    except Exception as e:
        logger.error(f"❌ LLM extraction failed: {e}")
        return None


def _parse_name_from_response(response: str) -> Optional[str]:
    """
    Parse patient name from LLM response.
    
    CRITICAL FIX v2: More aggressive cleaning of OCR artifacts.
    
    LLM might return:
    - "George Orwell" ✓
    - "The patient name is George Orwell" ✓
    - "Patient: George Orwell" ✓
    - "George.Orwell" → Clean to "George Orwell" ✓
    - Long explanation ✗
    
    Args:
        response: Raw LLM output
    
    Returns:
        Clean patient name or None
    """
    
    # Remove common prefixes
    response = response.strip()
    response = re.sub(r'^(The patient name is|Patient name:|Patient:)\s*', '', response, flags=re.IGNORECASE)
    response = response.strip()
    
    # If response is too long, it's probably an explanation, not a name
    if len(response) > 100:
        # Try to extract name pattern: "FirstName LastName"
        name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b', response)
        if name_match:
            response = name_match.group(1)
        else:
            return None
    
    # CRITICAL FIX v2: Clean OCR artifacts
    # Replace dots, underscores, and multiple spaces with single space
    response = re.sub(r'[\._]+', ' ', response)  # George.Orwell → George Orwell
    response = re.sub(r'[^\w\s\-]', '', response)  # Remove special chars except hyphens
    response = re.sub(r'\s+', ' ', response)  # Normalize spaces
    response = response.strip()
    
    # Remove trailing numbers/IDs (e.g., "John Doe 12345" → "John Doe")
    response = re.sub(r'\s+[-\d]+$', '', response)
    
    # Validate: Should be 2-4 words, each capitalized
    words = response.split()
    if 2 <= len(words) <= 4:
        # Check if looks like a name (capitalized words)
        if all(word[0].isupper() if word else False for word in words):
            return response
    
    return None


def validate_with_llm(ocr_data: Dict[str, str], raw_text: str) -> Dict[str, str]:
    """
    Validate and enhance OCR data using LLM.
    
    Currently focuses on patient name extraction.
    Can be expanded to validate amounts, dates, etc.
    
    Args:
        ocr_data: Dictionary of extracted claim data
        raw_text: Raw OCR text from image
    
    Returns:
        Enhanced data dictionary
    """
    
    if not is_ollama_available():
        logger.info("Ollama not available - returning original OCR data")
        return ocr_data
    
    # Make a copy so we don't modify original
    enhanced_data = ocr_data.copy()
    
    # Extract patient name if OCR failed
    current_name = ocr_data.get("Client", "NOTFOUND")
    
    if current_name == "NOTFOUND" or len(current_name.strip()) < 3:
        logger.info("Patient name missing or invalid, trying LLM extraction...")
        
        llm_name = extract_patient_name(raw_text, current_name)
        
        if llm_name:
            enhanced_data["Client"] = llm_name
            enhanced_data["_llm_enhanced"] = True
            enhanced_data["_llm_fields"] = "Client"
            logger.info(f"✅ LLM enhanced patient name: {llm_name}")
        else:
            logger.warning("⚠️  LLM could not improve patient name")
    
    return enhanced_data


def get_llm_status() -> Dict[str, any]:
    """
    Get status information about LLM availability.
    
    Useful for GUI display or debugging.
    
    Returns:
        Dictionary with status information
    """
    status = {
        "available": False,
        "model": "llama3.2:3b",
        "message": ""
    }
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            if "llama3.2:3b" in result.stdout or "llama3.2" in result.stdout:
                status["available"] = True
                status["message"] = "Ollama running with llama3.2:3b"
            else:
                status["message"] = "Ollama running but model not found"
        else:
            status["message"] = "Ollama service not responding"
            
    except FileNotFoundError:
        status["message"] = "Ollama not installed"
    except subprocess.TimeoutExpired:
        status["message"] = "Ollama timeout"
    except Exception as e:
        status["message"] = f"Error: {str(e)}"
    
    return status


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Setup logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    print("=" * 80)
    print("LLM VALIDATOR - TEST MODE (v2 - OCR Artifact Handling)")
    print("=" * 80)
    print()
    
    # Test 1: Check if Ollama is available
    print("TEST 1: Checking Ollama availability...")
    print("-" * 80)
    status = get_llm_status()
    print(f"Status: {status}")
    print()
    
    if not status["available"]:
        print("❌ Ollama not available. Tests skipped.")
        print("\nTo fix:")
        print("  1. Install Ollama from https://ollama.com")
        print("  2. Run: ollama pull llama3.2:3b")
        exit(1)
    
    # Test 2: Extract name with OCR artifacts (dots)
    print("TEST 2: Extract name with OCR dots (George.Orwell)...")
    print("-" * 80)
    
    sample_era_with_dots = """
    Claim #148057942
    Patient. George.Orwell
    Service Date: 9/1/2025
    Service Code: 90837
    Charged Rate: $300.00
    """
    
    extracted_name = extract_patient_name(sample_era_with_dots, "NOTFOUND")
    print(f"Extracted Name: {extracted_name}")
    print()
    
    if extracted_name == "George Orwell":
        print("✅ TEST PASSED: Correctly extracted 'George Orwell' from 'George.Orwell'")
    elif extracted_name:
        print(f"⚠️  TEST PARTIAL: Extracted '{extracted_name}' (expected 'George Orwell')")
    else:
        print("❌ TEST FAILED: Could not extract name")
    
    print()
    print("=" * 80)
    print("END OF TESTS")
    print("=" * 80)