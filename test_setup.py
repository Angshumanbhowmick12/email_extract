#!/usr/bin/env python3
"""
Quick test script to verify installation and data loading.
Does NOT require Groq API key - just validates setup.
"""
import json
import sys
from pathlib import Path


def test_imports():
    """Test that all required packages are installed."""
    print("Testing package imports...")
    try:
        from pydantic import BaseModel
        print("  ✓ pydantic installed")
    except ImportError:
        print("  ✗ pydantic not installed - run: pip install pydantic")
        return False
    
    try:
        from groq import Groq
        print("  ✓ groq installed")
    except ImportError:
        print("  ✗ groq not installed - run: pip install groq")
        return False
    
    return True


def test_files():
    """Test that all required files exist."""
    print("\nTesting required files...")
    required_files = [
        'schemas.py',
        'prompts.py',
        'extract.py',
        'evaluate.py',
        'emails_input.json',
        'ground_truth.json',
        'port_codes_reference.json'
    ]
    
    all_exist = True
    for filename in required_files:
        if Path(filename).exists():
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} missing")
            all_exist = False
    
    return all_exist


def test_data_loading():
    """Test that JSON files can be loaded."""
    print("\nTesting data loading...")
    
    try:
        with open('emails_input.json', 'r') as f:
            emails = json.load(f)
        print(f"  ✓ Loaded {len(emails)} emails")
    except Exception as e:
        print(f"  ✗ Failed to load emails_input.json: {e}")
        return False
    
    try:
        with open('ground_truth.json', 'r') as f:
            ground_truth = json.load(f)
        print(f"  ✓ Loaded {len(ground_truth)} ground truth entries")
    except Exception as e:
        print(f"  ✗ Failed to load ground_truth.json: {e}")
        return False
    
    try:
        with open('port_codes_reference.json', 'r') as f:
            ports = json.load(f)
        print(f"  ✓ Loaded {len(ports)} port references")
    except Exception as e:
        print(f"  ✗ Failed to load port_codes_reference.json: {e}")
        return False
    
    return True


def test_schemas():
    """Test that Pydantic schemas work."""
    print("\nTesting Pydantic schemas...")
    
    try:
        from schemas import EmailInput, ShipmentExtraction, PortReference
        
        # Test EmailInput
        email = EmailInput(
            id="TEST_001",
            subject="Test",
            body="Test body"
        )
        print(f"  ✓ EmailInput schema works")
        
        # Test ShipmentExtraction
        extraction = ShipmentExtraction(
            id="TEST_001",
            product_line="pl_sea_import_lcl",
            origin_port_code="HKHKG",
            origin_port_name="Hong Kong",
            destination_port_code="INMAA",
            destination_port_name="Chennai",
            incoterm="FOB",
            cargo_weight_kg=500.0,
            cargo_cbm=2.5,
            is_dangerous=False
        )
        print(f"  ✓ ShipmentExtraction schema works")
        
        # Test rounding
        extraction2 = ShipmentExtraction(
            id="TEST_002",
            cargo_weight_kg=123.456789,
            cargo_cbm=7.891234,
            is_dangerous=False
        )
        assert extraction2.cargo_weight_kg == 123.46
        assert extraction2.cargo_cbm == 7.89
        print(f"  ✓ Numeric rounding works (2 decimal places)")
        
        return True
    except Exception as e:
        print(f"  ✗ Schema test failed: {e}")
        return False


def test_prompts():
    """Test that prompt module works."""
    print("\nTesting prompt module...")
    
    try:
        from prompts import get_current_prompt, format_prompt, get_port_reference_text
        
        prompt_template = get_current_prompt()
        assert "product_line" in prompt_template
        assert "UN/LOCODE" in prompt_template
        print(f"  ✓ Prompt template loaded ({len(prompt_template)} chars)")
        
        # Test port reference formatting
        ports = [
            {"code": "HKHKG", "name": "Hong Kong"},
            {"code": "INMAA", "name": "Chennai"}
        ]
        ref_text = get_port_reference_text(ports)
        assert "HKHKG" in ref_text
        print(f"  ✓ Port reference formatting works")
        
        return True
    except Exception as e:
        print(f"  ✗ Prompt test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print(" "*15 + "INSTALLATION TEST")
    print("="*60)
    
    results = []
    
    results.append(("Package imports", test_imports()))
    results.append(("Required files", test_files()))
    results.append(("Data loading", test_data_loading()))
    results.append(("Pydantic schemas", test_schemas()))
    results.append(("Prompt module", test_prompts()))
    
    print("\n" + "="*60)
    print(" "*20 + "TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:<25} {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✓ All tests passed! Setup is complete.")
        print("\nNext steps:")
        print("  1. Set GROQ_API_KEY environment variable")
        print("  2. Run: python extract.py (generates output.json)")
        print("  3. Run: python evaluate.py (measures accuracy)")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())