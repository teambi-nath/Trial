#!/usr/bin/env python3
"""
Example usage script for the Patient ETL system.
This demonstrates how to use the ETL script programmatically.
"""

import os
import sys
from datetime import datetime

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config, ETLConfig
from patient_etl import PatientETL

def example_usage():
    """Example of how to use the Patient ETL system."""
    
    print("=" * 60)
    print("Patient ETL System - Usage Example")
    print("=" * 60)
    
    # Method 1: Using default configuration
    print("\n1. Using default configuration:")
    config = get_config()
    print(f"   Database: {config.db_name}")
    print(f"   Client ID: {config.client_id}")
    print(f"   Batch Size: {config.batch_size}")
    
    # Method 2: Creating custom configuration
    print("\n2. Creating custom configuration:")
    custom_config = ETLConfig(
        db_host="localhost",
        db_port=5432,
        db_name="test_db",
        db_user="test_user",
        db_password="test_pass",
        client_id=123,
        batch_size=500,
        log_level="DEBUG"
    )
    print(f"   Custom DB URL: {custom_config.db_url}")
    print(f"   Custom Client ID: {custom_config.client_id}")
    
    # Method 3: Environment variable override example
    print("\n3. Environment variable override example:")
    print("   Set environment variables like:")
    print("   export DB_HOST=myserver.com")
    print("   export CLIENT_ID=999")
    print("   export LOG_LEVEL=DEBUG")
    print("   The configuration will automatically pick these up.")
    
    # Method 4: Programmatic usage
    print("\n4. Programmatic ETL usage:")
    print("   # Initialize ETL")
    print("   etl = PatientETL(config)")
    print("   ")
    print("   # Run complete ETL process")
    print("   etl.run_etl(patient_file, appointment_file, client_id)")
    print("   ")
    print("   # Or run individual components:")
    print("   etl_id = etl.create_etl_metadata(client_id, file_path)")
    print("   etl.process_patient_data(df, etl_id)")
    print("   etl.process_patient_contact(df, etl_id)")
    print("   # ... etc")
    
    # Method 5: Command line usage
    print("\n5. Command line usage examples:")
    print("   # Basic usage with default files:")
    print("   python patient_etl.py")
    print("   ")
    print("   # With custom files:")
    print("   python patient_etl.py \\")
    print("     --patient-file /path/to/patients.xlsx \\")
    print("     --appointment-file /path/to/appointments.xlsx \\")
    print("     --client-id 897")
    
    # Method 6: Error handling example
    print("\n6. Error handling:")
    print("   The ETL system includes comprehensive error handling:")
    print("   - Invalid enum values → logged as warnings, stored as NULL")
    print("   - Missing files → FileNotFoundError with details")
    print("   - Database connection issues → Connection errors with retry info")
    print("   - Data validation failures → Detailed logging for debugging")
    
    print("\n" + "=" * 60)
    print("For more details, see README.md or run: python patient_etl.py --help")
    print("=" * 60)

def sample_data_structure():
    """Show expected data structure for Excel files."""
    
    print("\n" + "=" * 60)
    print("Expected Excel File Structure")
    print("=" * 60)
    
    print("\nPatient Demographic File - Required Columns:")
    required_columns = [
        "Patient Acct No",
        "Patient First Name", 
        "Patient Last Name",
        "Patient DOB",
        "Patient Gender",
        "Patient Status",
        "Patient Email",
        "Patient Cell Phone",
        "Patient Address Line 1",
        "Patient City",
        "Patient State",
        "Patient ZIP Code",
        # ... and many more
    ]
    
    for i, col in enumerate(required_columns, 1):
        print(f"   {i:2d}. {col}")
    print("   ... (and additional columns as shown in README.md)")
    
    print("\nData Validation Notes:")
    print("   - Patient Acct No: Required, must not be empty")
    print("   - Enum fields: Validated against database enum types")
    print("   - Date fields: Should be in Excel date format")
    print("   - Boolean fields: 'Yes'/'No' values for deceased status")
    print("   - Phone/Email: Optional, can be empty")

if __name__ == "__main__":
    example_usage()
    sample_data_structure()