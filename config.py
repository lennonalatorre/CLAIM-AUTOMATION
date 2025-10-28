"""
config.py - Configuration file for Claim Automation
---------------------------------------------------
Manages directories, counselor/insurer lists, and Tesseract OCR path.
"""

import os
import json
import pytesseract

# ═══════════════════════════════════════════════════════════════
# DIRECTORY PATHS
# ═══════════════════════════════════════════════════════════════

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
WORD_DIR = os.path.join(BASE_DIR, "WordFiles")
EXCEL_DIR = os.path.join(BASE_DIR, "ExcelFiles")
COUNSELORS_JSON = os.path.join(BASE_DIR, "counselors.json")
INSURERS_JSON = os.path.join(BASE_DIR, "insurers.json")

# Create directories if they don't exist
os.makedirs(WORD_DIR, exist_ok=True)
os.makedirs(EXCEL_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# TESSERACT OCR PATH CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Default Tesseract installation path for Windows
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Check if Tesseract exists at default path
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    print(f"✅ Tesseract found at: {TESSERACT_PATH}")
else:
    # Try alternative common paths
    alternative_paths = [
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME'))
    ]
    
    tesseract_found = False
    for alt_path in alternative_paths:
        if os.path.exists(alt_path):
            pytesseract.pytesseract.tesseract_cmd = alt_path
            print(f"✅ Tesseract found at: {alt_path}")
            tesseract_found = True
            break
    
    if not tesseract_found:
        print("⚠️  WARNING: Tesseract not found at default locations!")
        print("   Please install Tesseract OCR from:")
        print("   https://github.com/UB-Mannheim/tesseract/wiki")
        print("\n   Or manually set the path in config.py:")
        print("   TESSERACT_PATH = r'C:\\Your\\Custom\\Path\\tesseract.exe'")

# ═══════════════════════════════════════════════════════════════
# COUNSELOR MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def get_counselors():
    """
    Load counselor names from JSON file.
    Creates default counselor if file doesn't exist.
    
    Returns:
        list: List of counselor names
    """
    if not os.path.exists(COUNSELORS_JSON):
        save_counselors(["DrSmith"])
    
    try:
        with open(COUNSELORS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️  Could not load counselors: {e}")
        return []


def save_counselors(names):
    """
    Save counselor names to JSON file.
    Removes duplicates and sorts alphabetically.
    
    Args:
        names (list): List of counselor names to save
    """
    try:
        # Remove duplicates while preserving order, then sort
        unique_names = sorted(list(dict.fromkeys(names)))
        
        with open(COUNSELORS_JSON, "w", encoding="utf-8") as f:
            json.dump(unique_names, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(unique_names)} counselor(s)")
    except Exception as e:
        print(f"❌ Could not save counselors: {e}")


# ═══════════════════════════════════════════════════════════════
# INSURER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def get_insurers():
    """
    Load insurance company names from JSON file.
    Creates default insurers if file doesn't exist.
    
    Returns:
        list: List of insurance company names
    """
    if not os.path.exists(INSURERS_JSON):
        save_insurers(["Blue Cross", "Aetna", "Cigna", "UnitedHealthcare", "Medicare"])
    
    try:
        with open(INSURERS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️  Could not load insurers: {e}")
        return []


def save_insurers(names):
    """
    Save insurance company names to JSON file.
    Removes duplicates and sorts alphabetically.
    
    Args:
        names (list): List of insurance company names to save
    """
    try:
        # Remove duplicates while preserving order, then sort
        unique_names = sorted(list(dict.fromkeys(names)))
        
        with open(INSURERS_JSON, "w", encoding="utf-8") as f:
            json.dump(unique_names, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(unique_names)} insurer(s)")
    except Exception as e:
        print(f"❌ Could not save insurers: {e}")


# ═══════════════════════════════════════════════════════════════
# INSURANCE RATES (Optional Override)
# ═══════════════════════════════════════════════════════════════

INSURANCE_RATES_FILE = os.path.join(BASE_DIR, "insurance_rates.json")


def get_insurance_rate(insurance_name: str) -> float:
    """
    Get contracted rate for specific insurance company.
    
    Args:
        insurance_name (str): Name of insurance company
        
    Returns:
        float: Contracted rate if found, None otherwise
    """
    if not os.path.exists(INSURANCE_RATES_FILE):
        return None
    
    try:
        with open(INSURANCE_RATES_FILE, "r", encoding="utf-8") as f:
            rates = json.load(f)
            
        # Case-insensitive lookup
        insurance_lower = insurance_name.lower().strip()
        
        for key, value in rates.items():
            if key.lower().strip() == insurance_lower:
                return float(value)
        
        return None
    except Exception as e:
        print(f"⚠️  Could not load insurance rates: {e}")
        return None


def save_insurance_rate(insurance_name: str, rate: float):
    """
    Save contracted rate for specific insurance company.
    
    Args:
        insurance_name (str): Name of insurance company
        rate (float): Contracted rate amount
    """
    try:
        # Load existing rates
        if os.path.exists(INSURANCE_RATES_FILE):
            with open(INSURANCE_RATES_FILE, "r", encoding="utf-8") as f:
                rates = json.load(f)
        else:
            rates = {}
        
        # Update rate
        rates[insurance_name.lower().strip()] = float(rate)
        
        # Save back to file
        with open(INSURANCE_RATES_FILE, "w", encoding="utf-8") as f:
            json.dump(rates, f, indent=2)
        
        print(f"✅ Saved rate for {insurance_name}: ${rate:.2f}")
    except Exception as e:
        print(f"❌ Could not save insurance rate: {e}")


# ═══════════════════════════════════════════════════════════════
# INITIALIZATION CHECK
# ═══════════════════════════════════════════════════════════════

def verify_setup():
    """
    Verify that all required components are properly configured.
    Prints status of directories, Tesseract, and data files.
    """
    print("\n" + "═" * 80)
    print("CONFIGURATION VERIFICATION")
    print("═" * 80)
    
    # Check directories
    print(f"\n📁 Directories:")
    print(f"   Base Directory: {BASE_DIR}")
    print(f"   Excel Output: {EXCEL_DIR} {'✅' if os.path.exists(EXCEL_DIR) else '❌'}")
    print(f"   Word Output: {WORD_DIR} {'✅' if os.path.exists(WORD_DIR) else '❌'}")
    
    # Check Tesseract
    print(f"\n🔍 Tesseract OCR:")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"   Version: {version} ✅")
        print(f"   Path: {pytesseract.pytesseract.tesseract_cmd}")
    except Exception as e:
        print(f"   Status: NOT FOUND ❌")
        print(f"   Error: {e}")
    
    # Check data files
    print(f"\n📋 Data Files:")
    counselors = get_counselors()
    insurers = get_insurers()
    print(f"   Counselors: {len(counselors)} loaded ✅")
    print(f"   Insurers: {len(insurers)} loaded ✅")
    
    print("\n" + "═" * 80 + "\n")


# ═══════════════════════════════════════════════════════════════
# RUN VERIFICATION ON IMPORT (Optional)
# ═══════════════════════════════════════════════════════════════

# Uncomment the line below to run verification every time config is imported
# verify_setup()


# ═══════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Testing config.py...")
    verify_setup()
    
    # Test counselor functions
    print("\nTesting counselor management...")
    save_counselors(["Dr. Smith", "Dr. Jones", "Dr. Smith"])  # Duplicate test
    print(f"Counselors: {get_counselors()}")
    
    # Test insurer functions
    print("\nTesting insurer management...")
    save_insurers(["Aetna", "Blue Cross", "Aetna"])  # Duplicate test
    print(f"Insurers: {get_insurers()}")
    
    # Test insurance rates
    print("\nTesting insurance rates...")
    save_insurance_rate("Aetna", 135.56)
    save_insurance_rate("Blue Cross", 100.00)
    print(f"Aetna rate: ${get_insurance_rate('Aetna')}")
    print(f"Blue Cross rate: ${get_insurance_rate('blue cross')}")  # Case-insensitive test
    
    print("\n✅ All tests passed!")