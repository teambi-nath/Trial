# Patient ETL Script

This repository contains a Python ETL (Extract, Transform, Load) script for processing patient demographic and appointment data from Excel files and loading them into a PostgreSQL database.

## Features

- **Patient Demographic Processing**: Processes patient personal information with enum validation
- **Contact Information Management**: Handles patient contact details including email, phone, and address
- **Guarantor Information**: Manages patient guarantor data
- **Insurance Processing**: Supports primary, secondary, and tertiary insurance information
- **Employer Demographics**: Processes patient employment information
- **Appointment Data**: Handles appointment-related patient data
- **Enum Validation**: Validates data against PostgreSQL enum types
- **Configurable**: Supports configuration via environment variables and command-line arguments
- **Logging**: Comprehensive logging for monitoring and debugging
- **Error Handling**: Robust error handling with detailed logging

## Requirements

- Python 3.8+
- PostgreSQL database with appropriate schema
- Excel files in the expected format

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Trial
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up configuration (see Configuration section below)

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

### Configuration Options

- **DB_HOST**: Database host (default: 10.200.80.144)
- **DB_PORT**: Database port (default: 5432)
- **DB_NAME**: Database name (default: nath_pms_dw)
- **DB_USER**: Database username
- **DB_PASSWORD**: Database password
- **CLIENT_ID**: Client identifier (default: 897)
- **PATIENT_FILE_PATH**: Path to patient demographic Excel file
- **APPOINTMENT_FILE_PATH**: Path to appointment Excel file
- **LOG_LEVEL**: Logging level (default: INFO)
- **LOG_FILE**: Log file path (default: patient_etl.log)
- **BATCH_SIZE**: Database batch size for bulk operations (default: 1000)

## Usage

### Basic Usage

```bash
python patient_etl.py
```

### With Command-Line Arguments

```bash
python patient_etl.py --patient-file "/path/to/patient_data.xlsx" --appointment-file "/path/to/appointment_data.xlsx" --client-id 897
```

### Command-Line Options

- `--patient-file`: Path to patient demographic Excel file
- `--appointment-file`: Path to appointment Excel file
- `--client-id`: Client ID for the ETL process
- `--config-file`: Path to custom configuration file (optional)

## Database Schema

The script expects the following PostgreSQL tables and schemas:

### Tables
- `ecw.etl_metadata`: ETL process metadata
- `ecw.dim_patients_enum`: Patient demographic data
- `ecw.patient_contact_enum`: Patient contact information
- `ecw.patient_guarantor_enum`: Patient guarantor information
- `ecw.patient_demographic_employer_enum`: Patient employer information
- `core.patient_insurances`: Patient insurance information
- `core.insurance_lookup`: Insurance company lookup

### Enum Types
- `ecw.patient_gender_enum`
- `ecw.patient_status_enum`
- `ecw.patient_ethnicity_enum`
- `ecw.patient_language_enum`
- `ecw.patient_marital_status_enum`
- `ecw.patient_race_enum`
- `core.insurance_type_enum`

## Excel File Format

### Patient Demographic File Expected Columns
- Patient Acct No
- Patient First Name
- Patient Middle Initial
- Patient Last Name
- Patient Preferred Name
- Patient Previous Name
- Patient DOB
- Patient Status
- Patient Gender
- Patient Ethnicity
- Patient Language
- Patient Marital Status
- Patient Race
- Patient Registration Date
- Patient Deceased
- Patient Email
- Patient Cell Phone
- Patient Home Phone
- Patient Work Phone
- Patient Address Line 1/2
- Patient City, State, ZIP Code
- Patient Country Code
- Guarantor information
- Insurance information (Primary, Secondary, Tertiary)
- Employer information

### Appointment File Expected Columns
Similar structure to patient demographic file but for appointment-related data.

## Logging

The script provides comprehensive logging:
- **INFO**: General process information
- **DEBUG**: Detailed processing information
- **WARNING**: Data validation warnings
- **ERROR**: Processing errors

Logs are written to both the console and a log file (default: `patient_etl.log`).

## Error Handling

- Invalid enum values are logged as warnings and stored as NULL
- Missing required data is handled gracefully
- Database connection errors are caught and logged
- Transaction rollback on failures

## Development

### Code Structure

- `patient_etl.py`: Main ETL script with PatientETL class
- `config.py`: Configuration management
- `requirements.txt`: Python dependencies
- `.env.example`: Example environment configuration

### Key Methods

- `process_patient_data()`: Processes main patient demographic data
- `process_patient_contact()`: Handles contact information
- `process_patient_guarantor()`: Manages guarantor data
- `process_patient_insurance()`: Processes insurance information
- `process_patient_employer()`: Handles employer data
- `validate_enum()`: Validates data against database enums

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions, please create an issue in the repository or contact the development team.
