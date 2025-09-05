"""
Patient Data ETL Script

This script processes patient demographic and appointment data from Excel files
and loads them into a PostgreSQL database with proper enum validation.
"""

import pandas as pd
from sqlalchemy import create_engine
import psycopg2
from psycopg2.extras import execute_batch
import logging
from typing import Optional, Set
import os
import sys
import argparse
from datetime import datetime
from config import get_config, ETLConfig

logger = logging.getLogger(__name__)


class PatientETL:
    """Patient ETL class for processing demographic and appointment data."""
    
    def __init__(self, config: ETLConfig):
        """Initialize ETL with configuration."""
        self.config = config
        self.db_url = config.db_url
        self.engine = create_engine(self.db_url)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    def get_enum_labels(self, conn, enum_qualified_name: str) -> Set[str]:
        """Get enum labels from PostgreSQL database."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.enumlabel
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE (n.nspname || '.' || t.typname) = %s
                ORDER BY e.enumsortorder;
            """, (enum_qualified_name,))
            return {r[0] for r in cur.fetchall()}

    def clean_str(self, x) -> Optional[str]:
        """Clean and normalize string values."""
        if pd.isna(x):
            return None
        s = str(x).strip()
        return s if s else None

    def normalize_for_match(self, x) -> Optional[str]:
        """Light normalization for matching (case-insensitive)."""
        if x is None:
            return None
        return x.strip()

    def validate_enum(self, value: Optional[str], allowed: Set[str]) -> Optional[str]:
        """
        Returns `value` if it matches an allowed enum label (case-sensitive exact).
        If not matched (including None), returns None to insert as NULL.
        """
        if value is None:
            return None
        # Try direct match
        if value in allowed:
            return value
        # Try case-insensitive match
        lowered = value.lower()
        for label in allowed:
            if label.lower() == lowered:
                return label
        # No match -> NULL (you could also raise to fail fast)
        logger.warning(f"Invalid enum value '{value}' not found in allowed values: {allowed}")
        return None

    def convert_deceased_status(self, deceased_value) -> Optional[bool]:
        """Convert 'Yes'/'No' to boolean with debugging."""
        logger.debug(f"Original deceased value: '{deceased_value}'")
        if pd.isna(deceased_value) or str(deceased_value).strip() == '':
            logger.debug("Returning None (NULL) because value is NaN or empty")
            return None
        
        # Normalize the string to lowercase and compare
        deceased_value = str(deceased_value).strip().lower()
        logger.debug(f"Normalized deceased value: '{deceased_value}'")
        
        if deceased_value == "yes":
            logger.debug("Returning True for 'Yes'")
            return True
        elif deceased_value == "no":
            logger.debug("Returning False for 'No'")
            return False
        
        # If the value doesn't match 'yes' or 'no', return None
        logger.warning(f"Returning None for unrecognized deceased value '{deceased_value}'")
        return None

    def upsert_lookup_table(self, table_name: str, column_name: str, unique_values: list):
        """Insert unique values into lookup tables."""
        upsert_query = f"""
        INSERT INTO ecw.{table_name} ({column_name})
        VALUES (%s)
        ON CONFLICT ({column_name}) DO NOTHING;
        """
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cursor:
                for value in unique_values:
                    cursor.execute(upsert_query, (value,))

    def create_etl_metadata(self, client_id: int, filepath: str) -> int:
        """Create ETL metadata record and return etl_id."""
        etl_data = {
            'client_id': client_id,
            'filepath': filepath,
            'created_by': 'system',
            'last_updated_by': 'system',
            'creation_dt': pd.to_datetime('now'),
            'last_update_dt': pd.to_datetime('now'),
            'comments': 'Patient demographic data load'
        }

        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ecw.etl_metadata (client_id, filepath, created_by, last_updated_by, creation_dt, last_update_dt, comments)
                    VALUES (%(client_id)s, %(filepath)s, %(created_by)s, %(last_updated_by)s, %(creation_dt)s, %(last_update_dt)s, %(comments)s)
                    RETURNING etl_id;
                """, etl_data)
                
                etl_id = cursor.fetchone()[0]
                logger.info(f"Created ETL metadata record with ID: {etl_id}")
                return etl_id

    def process_patient_data(self, df: pd.DataFrame, etl_id: int):
        """Process patient demographic data."""
        with psycopg2.connect(self.db_url) as conn:
            conn.autocommit = False

            # Fetch enum label sets
            gender_labels = self.get_enum_labels(conn, "ecw.patient_gender_enum")
            status_labels = self.get_enum_labels(conn, "ecw.patient_status_enum")
            ethnicity_labels = self.get_enum_labels(conn, "ecw.patient_ethnicity_enum")
            language_labels = self.get_enum_labels(conn, "ecw.patient_language_enum")
            marital_labels = self.get_enum_labels(conn, "ecw.patient_marital_status_enum")
            race_labels = self.get_enum_labels(conn, "ecw.patient_race_enum")

            # Process patients
            pat_rows = []
            for _, r in df.iterrows():
                acct = self.clean_str(r.get("Patient Acct No"))
                if not acct:
                    continue

                pat_rows.append({
                    "patient_acct_no": acct,
                    "patient_first_name": self.clean_str(r.get("Patient First Name")),
                    "patient_middle_initial": self.clean_str(r.get("Patient Middle Initial")),
                    "patient_last_name": self.clean_str(r.get("Patient Last Name")),
                    "patient_preferred_name": self.clean_str(r.get("Patient Preferred Name")),
                    "patient_previous_name": self.clean_str(r.get("Patient Previous Name")),
                    "patient_dob": r.get("Patient DOB"),
                    "patient_status": self.validate_enum(self.clean_str(r.get("Patient Status")), status_labels),
                    "patient_gender": self.validate_enum(self.clean_str(r.get("Patient Gender")), gender_labels),
                    "patient_ethnicity": self.validate_enum(self.clean_str(r.get("Patient Ethnicity")), ethnicity_labels),
                    "patient_language": self.validate_enum(self.clean_str(r.get("Patient Language")), language_labels),
                    "patient_marital_status": self.validate_enum(self.clean_str(r.get("Patient Marital Status")), marital_labels),
                    "patient_race": self.validate_enum(self.clean_str(r.get("Patient Race")), race_labels),
                    "patient_registration_date": r.get("Patient Registration Date"),
                    "patient_deceased": self.convert_deceased_status(r.get("Patient Deceased")),
                    "etl_id": etl_id
                })

            sql_pat = """
            INSERT INTO ecw.dim_patients_enum (
                patient_acct_no, patient_first_name, patient_middle_initial, patient_last_name,
                patient_preferred_name, patient_previous_name, patient_dob,
                patient_status, patient_gender, patient_ethnicity, patient_language,
                patient_marital_status, patient_race, patient_registration_date,
                patient_deceased, etl_id
            )
            VALUES (
                %(patient_acct_no)s, %(patient_first_name)s, %(patient_middle_initial)s, %(patient_last_name)s,
                %(patient_preferred_name)s, %(patient_previous_name)s, %(patient_dob)s,
                %(patient_status)s::ecw.patient_status_enum,
                %(patient_gender)s::ecw.patient_gender_enum,
                %(patient_ethnicity)s::ecw.patient_ethnicity_enum,
                %(patient_language)s::ecw.patient_language_enum,
                %(patient_marital_status)s::ecw.patient_marital_status_enum,
                %(patient_race)s::ecw.patient_race_enum,
                %(patient_registration_date)s,
                %(patient_deceased)s, %(etl_id)s
            )
            ON CONFLICT (patient_acct_no) 
            DO UPDATE SET 
                patient_first_name = EXCLUDED.patient_first_name,
                patient_middle_initial = EXCLUDED.patient_middle_initial,
                patient_last_name = EXCLUDED.patient_last_name,
                patient_preferred_name = EXCLUDED.patient_preferred_name,
                patient_previous_name = EXCLUDED.patient_previous_name,
                patient_dob = EXCLUDED.patient_dob,
                patient_status = EXCLUDED.patient_status::ecw.patient_status_enum,
                patient_gender = EXCLUDED.patient_gender::ecw.patient_gender_enum,
                patient_ethnicity = EXCLUDED.patient_ethnicity::ecw.patient_ethnicity_enum,
                patient_language = EXCLUDED.patient_language::ecw.patient_language_enum,
                patient_marital_status = EXCLUDED.patient_marital_status::ecw.patient_marital_status_enum,
                patient_race = EXCLUDED.patient_race::ecw.patient_race_enum,
                patient_registration_date = EXCLUDED.patient_registration_date,
                patient_deceased = EXCLUDED.patient_deceased,
                etl_id = EXCLUDED.etl_id;
            """

            with conn.cursor() as cur:
                execute_batch(cur, sql_pat, pat_rows, page_size=self.config.batch_size)

            conn.commit()
            logger.info(f"Processed {len(pat_rows)} patient records")

    def process_patient_contact(self, df: pd.DataFrame, etl_id: int):
        """Process patient contact data."""
        with psycopg2.connect(self.db_url) as conn:
            for index, row in df.iterrows():
                patient_contact_data = {
                    'patient_acct_no': row['Patient Acct No'],
                    'patient_email': row.get('Patient Email'),
                    'patient_email_not_provided_reason': row.get('Patient Email Not Provided Reason'),
                    'patient_cell_phone': row.get('Patient Cell Phone'),
                    'patient_home_phone': row.get('Patient Home Phone'),
                    'patient_work_phone': row.get('Patient Work Phone'),
                    'patient_address_line_1': row.get('Patient Address Line 1'),
                    'patient_address_line_2': row.get('Patient Address Line 2'),
                    'patient_city': row.get('Patient City'),
                    'patient_state': row.get('Patient State'),
                    'patient_zip_code': row.get('Patient ZIP Code'),
                    'patient_country_code': row.get('Patient Country Code'),
                    'mother_1_name': row.get('Mother 1 Name'),
                    'mother_1_phone_no': row.get('Mother 1 Phone No'),
                    'mother_1_email': row.get('Mother 1 E-mail'),
                    'father_1_name': row.get('Father 1 Name'),
                    'father_1_phone_no': row.get('Father 1 Phone No'),
                    'father_1_email': row.get('Father 1 E-mail'),
                    'etl_id': etl_id
                }

                contact_upsert_query = """
                INSERT INTO ecw.patient_contact_enum (
                    patient_acct_no, patient_email, patient_email_not_provided_reason, patient_cell_phone, patient_home_phone, 
                    patient_work_phone, patient_address_line_1, patient_address_line_2, patient_city, patient_state, 
                    patient_zip_code, patient_country_code, mother_1_name, mother_1_phone_no, mother_1_email, father_1_name, 
                    father_1_phone_no, father_1_email, etl_id)
                VALUES (
                    %(patient_acct_no)s, %(patient_email)s, %(patient_email_not_provided_reason)s, %(patient_cell_phone)s, %(patient_home_phone)s, 
                    %(patient_work_phone)s, %(patient_address_line_1)s, %(patient_address_line_2)s, %(patient_city)s, %(patient_state)s, 
                    %(patient_zip_code)s, %(patient_country_code)s, %(mother_1_name)s, %(mother_1_phone_no)s, %(mother_1_email)s, 
                    %(father_1_name)s, %(father_1_phone_no)s, %(father_1_email)s, %(etl_id)s)
                ON CONFLICT (patient_acct_no) 
                DO UPDATE SET 
                    patient_email = EXCLUDED.patient_email,
                    patient_email_not_provided_reason = EXCLUDED.patient_email_not_provided_reason,
                    patient_cell_phone = EXCLUDED.patient_cell_phone,
                    patient_home_phone = EXCLUDED.patient_home_phone,
                    patient_work_phone = EXCLUDED.patient_work_phone,
                    patient_address_line_1 = EXCLUDED.patient_address_line_1,
                    patient_address_line_2 = EXCLUDED.patient_address_line_2,
                    patient_city = EXCLUDED.patient_city,
                    patient_state = EXCLUDED.patient_state,
                    patient_zip_code = EXCLUDED.patient_zip_code,
                    patient_country_code = EXCLUDED.patient_country_code,
                    mother_1_name = EXCLUDED.mother_1_name,
                    mother_1_phone_no = EXCLUDED.mother_1_phone_no,
                    mother_1_email = EXCLUDED.mother_1_email,
                    father_1_name = EXCLUDED.father_1_name,
                    father_1_phone_no = EXCLUDED.father_1_phone_no,
                    father_1_email = EXCLUDED.father_1_email,
                    etl_id = EXCLUDED.etl_id;
                """

                with conn.cursor() as cursor:
                    cursor.execute(contact_upsert_query, patient_contact_data)

        logger.info("Patient contact processing completed successfully!")

    def process_patient_guarantor(self, df: pd.DataFrame, etl_id: int):
        """Process patient guarantor data."""
        with psycopg2.connect(self.db_url) as conn:
            for index, row in df.iterrows():
                guarantor_data = {
                    'patient_acct_no': row['Patient Acct No'],
                    'guarantor_acct_no': row.get('Guarantor Acct No'),
                    'guarantor_name': row.get('Guarantor Name'),
                    'guarantor_mailing_address_line_1': row.get('Guarantor Mailing Address Line 1'),
                    'guarantor_mailing_address_line_2': row.get('Guarantor Mailing Address Line 2'),
                    'guarantor_mailing_city': row.get('Guarantor Mailing City'),
                    'guarantor_mailing_state': row.get('Guarantor Mailing State'),
                    'guarantor_mailing_zip_code': row.get('Guarantor Mailing ZIP Code'),
                    'guarantor_phone_no': row.get('Guarantor Phone No'),
                    'etl_id': etl_id
                }

                guarantor_upsert_query = """
                INSERT INTO ecw.patient_guarantor_enum (
                    patient_acct_no, guarantor_acct_no, guarantor_name, 
                    guarantor_mailing_address_line_1, guarantor_mailing_address_line_2, 
                    guarantor_mailing_city, guarantor_mailing_state, 
                    guarantor_mailing_zip_code, guarantor_phone_no, etl_id
                ) VALUES (
                    %(patient_acct_no)s, %(guarantor_acct_no)s, %(guarantor_name)s, 
                    %(guarantor_mailing_address_line_1)s, %(guarantor_mailing_address_line_2)s, 
                    %(guarantor_mailing_city)s, %(guarantor_mailing_state)s, 
                    %(guarantor_mailing_zip_code)s, %(guarantor_phone_no)s, %(etl_id)s
                )
                ON CONFLICT (patient_acct_no) 
                DO UPDATE SET 
                    guarantor_acct_no = EXCLUDED.guarantor_acct_no,
                    guarantor_name = EXCLUDED.guarantor_name,
                    guarantor_mailing_address_line_1 = EXCLUDED.guarantor_mailing_address_line_1,
                    guarantor_mailing_address_line_2 = EXCLUDED.guarantor_mailing_address_line_2,
                    guarantor_mailing_city = EXCLUDED.guarantor_mailing_city,
                    guarantor_mailing_state = EXCLUDED.guarantor_mailing_state,
                    guarantor_mailing_zip_code = EXCLUDED.guarantor_mailing_zip_code,
                    guarantor_phone_no = EXCLUDED.guarantor_phone_no,
                    etl_id = EXCLUDED.etl_id;
                """

                with conn.cursor() as cursor:
                    cursor.execute(guarantor_upsert_query, guarantor_data)

        logger.info("Patient guarantor processing completed successfully!")

    def get_or_insert_insurance(self, insurance_name: str, cursor) -> int:
        """Get or insert insurance name and return its insurance_id."""
        cursor.execute("""
            SELECT insurance_id FROM core.insurance_lookup WHERE insurance_name = %s;
        """, (insurance_name,))
        result = cursor.fetchone()
        if result:
            return result[0]

        cursor.execute("""
            INSERT INTO core.insurance_lookup (insurance_name, created_by, updated_by)
            VALUES (%s, %s, %s)
            RETURNING insurance_id;
        """, (insurance_name, 'system', 'system'))
        return cursor.fetchone()[0]

    def get_insurance_type_enum(self, insurance_type: str, cursor):
        """Get insurance type enum."""
        cursor.execute("""
            SELECT $1::core.insurance_type_enum;
        """, (insurance_type,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None

    def record_exists_and_changed(self, patient_acct_no: str, insurance_id: int, 
                                 insurance_type: str, new_data: dict, cursor) -> bool:
        """Check if the record exists and if there are any differences."""
        cursor.execute("""
            SELECT subscriber_number, group_name, group_no, insurance_class
            FROM core.patient_insurances
            WHERE client_patient_id = %s AND insurance_id = %s AND insurance_type = %s;
        """, (patient_acct_no, insurance_id, insurance_type))
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            return existing_record != (new_data['subscriber_number'], new_data['group_name'],
                                     new_data['group_no'], new_data['insurance_class'])
        return True

    def process_patient_insurance(self, df: pd.DataFrame, etl_id: int, client_id: int):
        """Process patient insurance data."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cursor:
                for index, row in df.iterrows():
                    primary_insurance = row['Primary Insurance Name'] if pd.notna(row['Primary Insurance Name']) else None
                    secondary_insurance = row['Secondary Insurance Name'] if pd.notna(row['Secondary Insurance Name']) else None
                    tertiary_insurance = row['Tertiary Insurance Name'] if pd.notna(row['Tertiary Insurance Name']) else None

                    insurance_data = []

                    # Process primary insurance
                    if primary_insurance and row.get('Primary Insurance Subscriber No'):
                        insurance_id_primary = self.get_or_insert_insurance(primary_insurance, cursor)
                        insurance_type_primary = self.get_insurance_type_enum('primary', cursor)

                        new_data_primary = {
                            'insurance_name': primary_insurance,
                            'subscriber_number': row['Primary Insurance Subscriber No'],
                            'group_name': row.get('Primary Insurance Group Name'),
                            'group_no': row.get('Primary Insurance Group No'),
                            'insurance_class': row.get('Primary Insurance Class')
                        }

                        if self.record_exists_and_changed(row['Patient Acct No'], insurance_id_primary, 
                                                         insurance_type_primary, new_data_primary, cursor):
                            insurance_data.append({
                                'client_patient_id': row['Patient Acct No'],
                                'insurance_id': insurance_id_primary,
                                'insurance_type': insurance_type_primary,
                                'subscriber_number': row['Primary Insurance Subscriber No'],
                                'group_name': row.get('Primary Insurance Group Name'),
                                'group_no': row.get('Primary Insurance Group No'),
                                'insurance_class': row.get('Primary Insurance Class'),
                                'etl_id': etl_id,
                                'client_id': client_id
                            })

                    # Process secondary insurance
                    if secondary_insurance and row.get('Secondary Insurance Subscriber No'):
                        insurance_id_secondary = self.get_or_insert_insurance(secondary_insurance, cursor)
                        insurance_type_secondary = self.get_insurance_type_enum('secondary', cursor)

                        new_data_secondary = {
                            'insurance_name': secondary_insurance,
                            'subscriber_number': row['Secondary Insurance Subscriber No'],
                            'group_name': row.get('Secondary Insurance Group Name'),
                            'group_no': row.get('Secondary Insurance Group No'),
                            'insurance_class': row.get('Secondary Insurance Class')
                        }

                        if self.record_exists_and_changed(row['Patient Acct No'], insurance_id_secondary,
                                                         insurance_type_secondary, new_data_secondary, cursor):
                            insurance_data.append({
                                'client_patient_id': row['Patient Acct No'],
                                'insurance_id': insurance_id_secondary,
                                'insurance_type': insurance_type_secondary,
                                'subscriber_number': row['Secondary Insurance Subscriber No'],
                                'group_name': row.get('Secondary Insurance Group Name'),
                                'group_no': row.get('Secondary Insurance Group No'),
                                'insurance_class': row.get('Secondary Insurance Class'),
                                'etl_id': etl_id,
                                'client_id': client_id
                            })

                    # Process tertiary insurance
                    if tertiary_insurance and row.get('Tertiary Insurance Subscriber No'):
                        insurance_id_tertiary = self.get_or_insert_insurance(tertiary_insurance, cursor)
                        insurance_type_tertiary = self.get_insurance_type_enum('tertiary', cursor)

                        new_data_tertiary = {
                            'insurance_name': tertiary_insurance,
                            'subscriber_number': row['Tertiary Insurance Subscriber No'],
                            'group_name': row.get('Tertiary Insurance Group Name'),
                            'group_no': row.get('Tertiary Insurance Group No'),
                            'insurance_class': row.get('Tertiary Insurance Class')
                        }

                        if self.record_exists_and_changed(row['Patient Acct No'], insurance_id_tertiary,
                                                         insurance_type_tertiary, new_data_tertiary, cursor):
                            insurance_data.append({
                                'client_patient_id': row['Patient Acct No'],
                                'insurance_id': insurance_id_tertiary,
                                'insurance_type': insurance_type_tertiary,
                                'subscriber_number': row['Tertiary Insurance Subscriber No'],
                                'group_name': row.get('Tertiary Insurance Group Name'),
                                'group_no': row.get('Tertiary Insurance Group No'),
                                'insurance_class': row.get('Tertiary Insurance Class'),
                                'etl_id': etl_id,
                                'client_id': client_id
                            })

                    # Insert data into patient_insurances table
                    for insurance in insurance_data:
                        insurance_insert_query = """
                        INSERT INTO core.patient_insurances (
                            client_patient_id, insurance_id, insurance_type, subscriber_number, 
                            group_name, group_no, insurance_class, etl_id, client_id
                        ) VALUES (
                            %(client_patient_id)s, %(insurance_id)s, %(insurance_type)s, %(subscriber_number)s, 
                            %(group_name)s, %(group_no)s, %(insurance_class)s, %(etl_id)s, %(client_id)s
                        );
                        """
                        cursor.execute(insurance_insert_query, insurance)

        logger.info("ETL process completed successfully for patient insurance!")

    def process_patient_employer(self, df: pd.DataFrame, etl_id: int):
        """Process patient employer demographic data."""
        with psycopg2.connect(self.db_url) as conn:
            for index, row in df.iterrows():
                employer_data = {
                    'patient_acct_no': row['Patient Acct No'],
                    'patient_employer_name': row.get('Patient Employer Name'),
                    'patient_demographic_employer_name': row.get('Patient Demographic Employer Name'),
                    'patient_demographic_employment_status': row.get('Patient Demographic Employment Status'),
                    'patient_demographic_employer_address_line_1': row.get('Patient Demographic Employer Address Line 1'),
                    'patient_demographic_employer_address_line_2': row.get('Patient Demographic Employer Address Line 2'),
                    'patient_demographic_employer_city': row.get('Patient Demographic Employer City'),
                    'patient_demographic_employer_state': row.get('Patient Demographic Employer State'),
                    'patient_demographic_employer_zip_code': row.get('Patient Demographic Employer ZIP Code'),
                    'patient_demographic_employer_phone_no': row.get('Patient Demographic Employer Phone No'),
                    'etl_id': etl_id
                }

                upsert_query = """
                INSERT INTO ecw.patient_demographic_employer_enum (
                    patient_acct_no, patient_employer_name, patient_demographic_employer_name,
                    patient_demographic_employment_status, patient_demographic_employer_address_line_1,
                    patient_demographic_employer_address_line_2, patient_demographic_employer_city,
                    patient_demographic_employer_state, patient_demographic_employer_zip_code,
                    patient_demographic_employer_phone_no, etl_id
                ) VALUES (
                    %(patient_acct_no)s, %(patient_employer_name)s, %(patient_demographic_employer_name)s,
                    %(patient_demographic_employment_status)s, %(patient_demographic_employer_address_line_1)s,
                    %(patient_demographic_employer_address_line_2)s, %(patient_demographic_employer_city)s,
                    %(patient_demographic_employer_state)s, %(patient_demographic_employer_zip_code)s,
                    %(patient_demographic_employer_phone_no)s, %(etl_id)s
                )
                ON CONFLICT (patient_acct_no) 
                DO UPDATE SET 
                    patient_employer_name = EXCLUDED.patient_employer_name,
                    patient_demographic_employer_name = EXCLUDED.patient_demographic_employer_name,
                    patient_demographic_employment_status = EXCLUDED.patient_demographic_employment_status,
                    patient_demographic_employer_address_line_1 = EXCLUDED.patient_demographic_employer_address_line_1,
                    patient_demographic_employer_address_line_2 = EXCLUDED.patient_demographic_employer_address_line_2,
                    patient_demographic_employer_city = EXCLUDED.patient_demographic_employer_city,
                    patient_demographic_employer_state = EXCLUDED.patient_demographic_employer_state,
                    patient_demographic_employer_zip_code = EXCLUDED.patient_demographic_employer_zip_code,
                    patient_demographic_employer_phone_no = EXCLUDED.patient_demographic_employer_phone_no,
                    etl_id = EXCLUDED.etl_id;
                """

                with conn.cursor() as cursor:
                    cursor.execute(upsert_query, employer_data)

        logger.info("Patient employer processing completed successfully!")

    def run_etl(self, patient_file_path: str, appointment_file_path: str, client_id: int):
        """Run the complete ETL process."""
        try:
            logger.info(f"Starting ETL process for client {client_id}")
            
            # Read Excel files
            logger.info(f"Reading patient data from: {patient_file_path}")
            df = pd.read_excel(patient_file_path)
            df.columns = df.columns.str.strip()
            
            logger.info(f"Reading appointment data from: {appointment_file_path}")
            df_appt = pd.read_excel(appointment_file_path)
            df_appt = df_appt.astype(object).where(pd.notna(df_appt), None)
            df_appt.columns = df_appt.columns.str.strip()

            # Create ETL metadata
            etl_id = self.create_etl_metadata(client_id, patient_file_path)

            # Process all data tables
            logger.info("Processing patient demographic data...")
            self.process_patient_data(df, etl_id)
            
            logger.info("Processing patient contact data...")
            self.process_patient_contact(df, etl_id)
            
            logger.info("Processing patient guarantor data...")
            self.process_patient_guarantor(df, etl_id)
            
            logger.info("Processing patient insurance data...")
            self.process_patient_insurance(df, etl_id, client_id)
            
            logger.info("Processing patient employer data...")
            self.process_patient_employer(df, etl_id)

            # Process appointment data if needed
            if not df_appt.empty:
                logger.info("Processing appointment patient data...")
                self.process_patient_data(df_appt, etl_id)

            logger.info("ETL process completed successfully!")
            
        except Exception as e:
            logger.error(f"ETL process failed: {str(e)}")
            raise


def main():
    """Main function to run ETL with configuration."""
    parser = argparse.ArgumentParser(description='Patient ETL Script')
    parser.add_argument('--patient-file', help='Path to patient demographic Excel file')
    parser.add_argument('--appointment-file', help='Path to appointment Excel file')
    parser.add_argument('--client-id', type=int, help='Client ID')
    parser.add_argument('--config-file', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Get configuration
    config = get_config()
    
    # Override with command line arguments if provided
    if args.patient_file:
        config.patient_file_path = args.patient_file
    if args.appointment_file:
        config.appointment_file_path = args.appointment_file
    if args.client_id:
        config.client_id = args.client_id
    
    # Use default file paths if not specified
    if not config.patient_file_path:
        config.patient_file_path = r"H:\AR PRODUCTION REPORTS\Business Intelligence\Python Automation\Pradip\Data_BOT\ECW_BOT\Ebo_downloader_bot\Downloaded_Reports\897\08262025\41.01 - Patient Demographic Report.xlsx"
    
    if not config.appointment_file_path:
        config.appointment_file_path = r"H:\AR PRODUCTION REPORTS\Business Intelligence\Python Automation\Pradip\Data_BOT\ECW_BOT\Ebo_downloader_bot\Downloaded_Reports\897\08262025\4.02 - Encounter Patient Download_appnt.xlsx"
    
    # Initialize and run ETL
    etl = PatientETL(config)
    etl.run_etl(config.patient_file_path, config.appointment_file_path, config.client_id)


if __name__ == "__main__":
    main()