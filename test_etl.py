#!/usr/bin/env python3
"""
Simple test script for patient_etl.py without database dependencies
"""

import pandas as pd
import sys
import os

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config, ETLConfig
from patient_etl import PatientETL

def test_configuration():
    """Test configuration loading."""
    print("Testing configuration...")
    config = get_config()
    print(f"✓ Database URL: {config.db_url}")
    print(f"✓ Client ID: {config.client_id}")
    print(f"✓ Batch size: {config.batch_size}")
    print(f"✓ Log level: {config.log_level}")
    
def test_etl_class_initialization():
    """Test ETL class initialization."""
    print("\nTesting ETL class initialization...")
    config = get_config()
    etl = PatientETL(config)
    print(f"✓ ETL instance created with DB URL: {etl.db_url}")
    
def test_utility_functions():
    """Test utility functions."""
    print("\nTesting utility functions...")
    config = get_config()
    etl = PatientETL(config)
    
    # Test clean_str function
    assert etl.clean_str("  test  ") == "test"
    assert etl.clean_str("") is None
    assert etl.clean_str(None) is None
    assert etl.clean_str(pd.NA) is None
    print("✓ clean_str function works correctly")
    
    # Test convert_deceased_status function
    assert etl.convert_deceased_status("Yes") is True
    assert etl.convert_deceased_status("No") is False
    assert etl.convert_deceased_status("YES") is True
    assert etl.convert_deceased_status("no") is False
    assert etl.convert_deceased_status("") is None
    assert etl.convert_deceased_status(None) is None
    print("✓ convert_deceased_status function works correctly")
    
    # Test validate_enum function
    allowed_values = {"Active", "Inactive", "Pending"}
    assert etl.validate_enum("Active", allowed_values) == "Active"
    assert etl.validate_enum("active", allowed_values) == "Active"
    assert etl.validate_enum("Invalid", allowed_values) is None
    assert etl.validate_enum(None, allowed_values) is None
    print("✓ validate_enum function works correctly")

def test_dataframe_processing():
    """Test DataFrame processing logic without database."""
    print("\nTesting DataFrame processing...")
    
    # Create sample data
    sample_data = {
        'Patient Acct No': ['P001', 'P002', ''],
        'Patient First Name': ['John', 'Jane', 'Bob'],
        'Patient Last Name': ['Doe', 'Smith', 'Johnson'],
        'Patient Gender': ['Male', 'Female', 'male'],
        'Patient Status': ['Active', 'active', 'Invalid'],
        'Patient Deceased': ['No', 'Yes', '']
    }
    
    df = pd.DataFrame(sample_data)
    
    config = get_config()
    etl = PatientETL(config)
    
    # Test row processing logic
    processed_rows = 0
    for _, row in df.iterrows():
        acct = etl.clean_str(row.get("Patient Acct No"))
        if acct:  # Only process rows with valid account numbers
            processed_rows += 1
            
            # Test data cleaning
            first_name = etl.clean_str(row.get("Patient First Name"))
            last_name = etl.clean_str(row.get("Patient Last Name"))
            deceased = etl.convert_deceased_status(row.get("Patient Deceased"))
            
            assert first_name is not None
            assert last_name is not None
            
    assert processed_rows == 2  # Should skip the row with empty account number
    print("✓ DataFrame processing logic works correctly")

def run_tests():
    """Run all tests."""
    print("=" * 50)
    print("Running Patient ETL Tests")
    print("=" * 50)
    
    try:
        test_configuration()
        test_etl_class_initialization()
        test_utility_functions()
        test_dataframe_processing()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed successfully!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        print("=" * 50)
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)