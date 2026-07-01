"""
Configuration module for the Opt-In Email Sample Generator.
All sensitive credentials are loaded from environment variables.
No hardcoded secrets are stored in this file.
"""

import os
from pathlib import Path

# --- API Keys (load from environment) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

AI_PROVIDER = "groq" if GROQ_API_KEY else ("openai" if OPENAI_API_KEY else None)

# --- Gmail SMTP / IMAP Credentials ---
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# --- SMTP / IMAP Settings ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"

# --- Rate Limiting ---
MAX_EMAILS_PER_HOUR = 20

# --- File Paths ---
BASE_DIR = Path(__file__).parent
SUBMISSIONS_CSV = BASE_DIR / "landing_page_submissions.csv"
ORDERS_CSV = BASE_DIR / "orders.csv"
INVOICES_DIR = BASE_DIR / "invoices"
LOG_FILE = BASE_DIR / "errors.log"

INVOICES_DIR.mkdir(exist_ok=True)

# --- Invoice Settings ---
CAMPAIGN_PRICE = 500.00
CAMPAIGN_EMAIL_COUNT = 30


def validate_config():
    """Ensure all required environment variables are set before running."""
    missing = []
    if not GMAIL_ADDRESS:
        missing.append("GMAIL_ADDRESS")
    if not GMAIL_APP_PASSWORD:
        missing.append("GMAIL_APP_PASSWORD")
    if not AI_PROVIDER:
        missing.append("GROQ_API_KEY or OPENAI_API_KEY")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please set them before running the application."
        )
    return True
