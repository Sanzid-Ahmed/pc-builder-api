# ==========================================
# Database Connection
# ==========================================

import os
import mysql.connector
from dotenv import load_dotenv


# ==========================================
# Load Environment Variables
# ==========================================

load_dotenv()


# ==========================================
# Database Configuration
# ==========================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),

    # Aiven requires SSL
    "ssl_disabled": False
}


# ==========================================
# Get Database Connection
# ==========================================

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)