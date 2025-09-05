#!/usr/bin/env python3
"""
System check script to verify all dependencies and configuration
for the Patient ETL system.
"""

import sys
import os
import subprocess

def check_python_version():
    """Check Python version compatibility."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires Python 3.8+)")
        return False

def check_dependencies():
    """Check required Python packages."""
    print("\nChecking Python dependencies...")
    
    required_packages = {
        'pandas': 'pandas>=1.5.0',
        'sqlalchemy': 'sqlalchemy>=1.4.0',
        'psycopg2': 'psycopg2-binary>=2.9.0',
        'openpyxl': 'openpyxl>=3.0.0'
    }
    
    all_ok = True
    
    for package, requirement in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is NOT installed (required: {requirement})")
            all_ok = False
    
    return all_ok

def check_files():
    """Check that all required files exist."""
    print("\nChecking required files...")
    
    required_files = [
        'patient_etl.py',
        'config.py',
        'requirements.txt',
        'README.md',
        '.env.example'
    ]
    
    all_ok = True
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for file in required_files:
        file_path = os.path.join(current_dir, file)
        if os.path.exists(file_path):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} is missing")
            all_ok = False
    
    return all_ok

def check_configuration():
    """Check configuration setup."""
    print("\nChecking configuration...")
    
    try:
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from config import get_config
        config = get_config()
        
        print(f"✓ Configuration loaded successfully")
        print(f"  - Database: {config.db_name}")
        print(f"  - Host: {config.db_host}")
        print(f"  - Port: {config.db_port}")
        print(f"  - Client ID: {config.client_id}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {str(e)}")
        return False

def check_etl_script():
    """Check that the ETL script can be imported."""
    print("\nChecking ETL script...")
    
    try:
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from patient_etl import PatientETL
        from config import get_config
        
        config = get_config()
        etl = PatientETL(config)
        
        print("✓ ETL script imports successfully")
        print("✓ PatientETL class can be instantiated")
        
        return True
        
    except Exception as e:
        print(f"✗ ETL script error: {str(e)}")
        return False

def show_install_instructions():
    """Show installation instructions if dependencies are missing."""
    print("\n" + "=" * 60)
    print("INSTALLATION INSTRUCTIONS")
    print("=" * 60)
    
    print("\n1. Install Python dependencies:")
    print("   pip install -r requirements.txt")
    
    print("\n2. Set up configuration:")
    print("   cp .env.example .env")
    print("   # Edit .env with your database credentials")
    
    print("\n3. Test the installation:")
    print("   python patient_etl.py --help")
    
    print("\n4. Run tests:")
    print("   python test_etl.py")

def main():
    """Run all system checks."""
    print("=" * 60)
    print("Patient ETL System Check")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_files(),
        check_dependencies(),
        check_configuration(),
        check_etl_script()
    ]
    
    all_passed = all(checks)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - System is ready!")
        print("\nNext steps:")
        print("1. Review and update .env file with your database credentials")
        print("2. Prepare your Excel files with the expected format")
        print("3. Run: python patient_etl.py --help for usage information")
    else:
        print("✗ SOME CHECKS FAILED - System needs attention")
        show_install_instructions()
    
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())