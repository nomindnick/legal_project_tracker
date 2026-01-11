"""Application configuration module.

Loads configuration from environment variables with sensible defaults
for development.
"""
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class.

    Reads configuration from environment variables. All sensitive values
    should be set via environment variables, never hardcoded.
    """

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'false').lower() in ('true', '1', 'yes')

    # Database settings
    # Default to SQLite for local development, PostgreSQL for production
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///legal_tracker.db'
    )

    # Handle Railway's postgres:// vs postgresql:// URL scheme
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            'postgres://', 'postgresql://', 1
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application settings
    APP_NAME = 'Legal Project Tracker'
