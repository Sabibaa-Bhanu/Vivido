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

    # Add expires_at column to users if it doesn't exist (for locked_until functionality)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN locked_until DATETIME")
    except sqlite3.OperationalError:
        pass  # Column already exists

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
        download_path TEXT,
        download_format TEXT,
        download_quality TEXT,
        has_watermark INTEGER DEFAULT 0,
        download_timestamp DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    # Remember-me sessions (persistent login tokens)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remember_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME DEFAULT (datetime('now', '+30 days')),
        revoked INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    # Add expires_at column to remember_sessions if it doesn't exist (for existing databases)
    # Note: SQLite doesn't support ALTER TABLE ADD COLUMN with non-constant default values,
    # so we add without default and then update existing rows
    try:
        cursor.execute("ALTER TABLE remember_sessions ADD COLUMN expires_at DATETIME")
        cursor.execute("UPDATE remember_sessions SET expires_at = datetime('now', '+30 days') WHERE expires_at IS NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Rate limiting for login attempts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rate_limits (
        rate_limit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT NOT NULL,
        attempt_count INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME DEFAULT (datetime('now', '+5 minutes')),
        UNIQUE(identifier)
    )
    """)

    # Add expires_at column to rate_limits if it doesn't exist (for existing databases)
    # Note: SQLite doesn't support ALTER TABLE ADD COLUMN with non-constant default values,
    # so we add without default and then update existing rows
    try:
        cursor.execute("ALTER TABLE rate_limits ADD COLUMN expires_at DATETIME")
        cursor.execute("UPDATE rate_limits SET expires_at = datetime('now', '+5 minutes') WHERE expires_at IS NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create indexes for performance
    # Index on remember_sessions.token_hash for token lookups
    try:
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_remember_sessions_token_hash 
        ON remember_sessions(token_hash)
        """)
    except sqlite3.OperationalError:
        pass  # Table may not exist or other issue
    
    # Index on remember_sessions.user_id for user session lookups
    try:
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_remember_sessions_user_id 
        ON remember_sessions(user_id)
        """)
    except sqlite3.OperationalError:
        pass  # Table may not exist or other issue
    
    # Index on remember_sessions.expires_at for cleanup queries
    try:
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_remember_sessions_expires_at 
        ON remember_sessions(expires_at)
        """)
    except sqlite3.OperationalError:
        pass  # Column may not exist
    
    # Index on rate_limits.identifier for rate limit lookups
    try:
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier 
        ON rate_limits(identifier)
        """)
    except sqlite3.OperationalError:
        pass  # Table may not exist or other issue
    
    # Index on rate_limits.expires_at for cleanup queries
    try:
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rate_limits_expires_at 
        ON rate_limits(expires_at)
        """)
    except sqlite3.OperationalError:
        pass  # Column may not exist

    conn.commit()
    conn.close()


def migrate_image_history_add_download_columns():
    """Add download-related columns to image_history table for existing databases."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Add download columns if they don't exist
    columns_to_add = [
        ("download_path", "TEXT"),
        ("download_format", "TEXT"),
        ("download_quality", "TEXT"),
        ("has_watermark", "INTEGER DEFAULT 0"),
        ("download_timestamp", "DATETIME"),
    ]
    
    for column_name, column_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE image_history ADD COLUMN {column_name} {column_def}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    conn.commit()
    conn.close()


def get_image_history(user_id):
    """Get image processing history for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT image_id, original_image_path, processed_image_path, style_applied, 
               processing_date, download_path, download_format, download_quality, 
               has_watermark, download_timestamp
        FROM image_history 
        WHERE user_id = ? 
        ORDER BY processing_date DESC
        """,
        (user_id,)
    )
    results = cursor.fetchall()
    conn.close()
    return results
    
