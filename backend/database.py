import sqlite3
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "vivido.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

print("DEBUG: Vivido DB path:", DB_PATH)


def get_connection():
    return sqlite3.connect(DB_PATH)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash BLOB NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME,
        is_active INTEGER DEFAULT 1,
        failed_login_attempts INTEGER DEFAULT 0,
        locked_until DATETIME
    )
    """)

    # Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        gateway_transaction_id TEXT UNIQUE,
        amount REAL NOT NULL,
        payment_status TEXT NOT NULL
            CHECK(payment_status IN ('PENDING','SUCCESS','FAILED')),
        payment_method TEXT NOT NULL
            CHECK(payment_method IN ('UPI','DEBIT_CARD','CREDIT_CARD','NETBANKING','WALLET')),
        transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    # ImageHistory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS image_history (
        image_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        original_image_path TEXT NOT NULL,
        processed_image_path TEXT NOT NULL,
        style_applied TEXT NOT NULL,
        processing_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
    
