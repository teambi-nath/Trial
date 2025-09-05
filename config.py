"""
Configuration file for Patient ETL script
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ETLConfig:
    """Configuration class for ETL parameters."""
    
    # Database configuration
    db_host: str = "10.200.80.144"
    db_port: int = 5432
    db_name: str = "nath_pms_dw"
    db_user: str = "Madhu"
    db_password: str = "Secure%402025"
    
    # Client configuration
    client_id: int = 897
    
    # File paths (can be overridden via environment variables or command line)
    patient_file_path: Optional[str] = None
    appointment_file_path: Optional[str] = None
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: str = "patient_etl.log"
    
    # Processing configuration
    batch_size: int = 1000
    
    @property
    def db_url(self) -> str:
        """Construct database URL from configuration."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def update_from_env(self):
        """Update configuration from environment variables."""
        self.db_host = os.getenv("DB_HOST", self.db_host)
        self.db_port = int(os.getenv("DB_PORT", self.db_port))
        self.db_name = os.getenv("DB_NAME", self.db_name)
        self.db_user = os.getenv("DB_USER", self.db_user)
        self.db_password = os.getenv("DB_PASSWORD", self.db_password)
        self.client_id = int(os.getenv("CLIENT_ID", self.client_id))
        self.patient_file_path = os.getenv("PATIENT_FILE_PATH", self.patient_file_path)
        self.appointment_file_path = os.getenv("APPOINTMENT_FILE_PATH", self.appointment_file_path)
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_file = os.getenv("LOG_FILE", self.log_file)
        self.batch_size = int(os.getenv("BATCH_SIZE", self.batch_size))


def get_config() -> ETLConfig:
    """Get configuration with environment variable overrides."""
    config = ETLConfig()
    config.update_from_env()
    return config