import re
import sqlite3
import bcrypt
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from backend.database import get_connection
from backend.database import create_tables

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiting constants
TOKEN_LOGIN_MAX_ATTEMPTS = 5  # Max failed token login attempts
TOKEN_LOGIN_WINDOW_SECONDS = 300  # 5 minute window


def _check_rate_limit(identifier: str) -> tuple[bool, str]:
    """
    Check if the identifier has exceeded rate limit using database.
    
    Args:
        identifier: A unique identifier (e.g., IP address hash, token hash)
    
    Returns:
        Tuple of (is_allowed, message)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Clean up expired rate limit entries
        cursor.execute(
            "DELETE FROM rate_limits WHERE expires_at < datetime('now')"
        )
        conn.commit()
        
        # Check current request
        cursor.execute(
            """SELECT attempt_count, expires_at FROM rate_limits 
               WHERE identifier = ? AND expires_at > datetime('now')""",
            (identifier,)
        )
        row = cursor.fetchone()
        
        if row:
            attempt_count = row[0]
            if attempt_count >= TOKEN_LOGIN_MAX_ATTEMPTS:
                return False, f"Too many failed attempts. Please try again later."
            # Increment attempt count
            cursor.execute(
                "UPDATE rate_limits SET attempt_count = attempt_count + 1 WHERE identifier = ?",
                (identifier,)
            )
        else:
            # Create new rate limit entry
            cursor.execute(
                """INSERT INTO rate_limits (identifier, attempt_count, expires_at) 
                   VALUES (?, 1, datetime('now', '+5 minutes'))""",
                (identifier,)
            )
        conn.commit()
        return True, ""
        
    except sqlite3.Error as e:
        logger.error(f"Database error in rate limit check: {e}")
        # Use fail-closed for security - deny on database errors to prevent abuse
        # This prevents attackers from exploiting DB issues to bypass rate limits
        return False, "Service temporarily unavailable. Please try again later."
    finally:
        if conn:
            conn.close()


def _record_successful_login(identifier: str) -> None:
    """Clear rate limit after successful login."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rate_limits WHERE identifier = ?", (identifier,))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error clearing rate limit: {e}")
    finally:
        if conn:
            conn.close()

create_tables()
# ------------------------
# Helper functions
# ------------------------

def is_valid_email(email: str) -> bool:
    """Check email format"""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def is_strong_password(password: str) -> bool:
    """Check password strength"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed_password


def _hash_remember_token(raw_token: str) -> str:
    """Hash remember-me token before storing in DB."""
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def create_remember_token(user_id: int, raw_token: str | None = None) -> str | None:
    """Create and persist a long-lived remember-me token for a user."""
    conn = None
    try:
        if not user_id:
            return None

        raw_token = (raw_token or "").strip() or secrets.token_urlsafe(48)
        token_hash = _hash_remember_token(raw_token)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO remember_sessions (user_id, token_hash, revoked)
            VALUES (?, ?, 0)
            ON CONFLICT(token_hash) DO UPDATE SET
                user_id = excluded.user_id,
                revoked = 0,
                created_at = CURRENT_TIMESTAMP
            """,
            (user_id, token_hash),
        )
        conn.commit()
        return raw_token
    except sqlite3.Error:
        return None
    finally:
        if conn:
            conn.close()


def revoke_remember_token(raw_token: str) -> bool:
    """Revoke a remember-me token."""
    conn = None
    try:
        token_hash = _hash_remember_token(raw_token)
        if not token_hash:
            return False

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE remember_sessions SET revoked = 1 WHERE token_hash = ?",
            (token_hash,),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        if conn:
            conn.close()


def login_with_remember_token(raw_token: str):
    """
    Authenticate user via a persistent remember-me token.

    Returns a dict compatible with login_user success payload.
    """
    # Apply rate limiting based on token hash
    token_hash = _hash_remember_token(raw_token) if raw_token else ""
    is_allowed, rate_limit_message = _check_rate_limit(token_hash)
    if not is_allowed:
        # Log failed attempt due to rate limiting
        logger.warning(f"Rate limit exceeded for token login attempt")
        return {"success": False, "message": rate_limit_message}
    
    conn = None
    try:
        if not raw_token:
            return {"success": False, "message": "Invalid token"}
            
        token_hash = _hash_remember_token(raw_token)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.email, u.last_login, u.is_active
            FROM remember_sessions rs
            JOIN users u ON u.user_id = rs.user_id
            WHERE rs.token_hash = ? AND rs.revoked = 0 AND (rs.expires_at IS NULL OR rs.expires_at > datetime('now'))
            """,
            (token_hash,),
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": "Session expired or not found"}

        user_id, username, email, last_login, is_active = row
        if not is_active:
            return {"success": False, "message": "Account is inactive. Contact support."}

        # Update last_login for remembered sign-ins as well
        new_last_login = datetime.now().isoformat()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE user_id = ?",
            (new_last_login, user_id),
        )
        conn.commit()

        # Clear rate limit after successful login
        _record_successful_login(token_hash)

        return {
            "success": True,
            "user_id": user_id,
            "username": username,
            "email": email,
            "last_login": new_last_login,
            "message": "Login successful",
        }
    except sqlite3.Error as e:
        logger.error(f"Database error during remember token login: {e}")
        return {"success": False, "message": "Database error. Please try again later."}
    except ValueError as e:
        # Re-raise validation errors with appropriate message
        logger.warning(f"Validation error during remember token login: {e}")
        return {"success": False, "message": str(e)}
    except Exception as e:
        # Log unexpected errors but don't expose details to user
        logger.exception("Unexpected error during remember token login")
        return {"success": False, "message": "An unexpected error occurred. Please try again later."}
    finally:
        if conn:
            conn.close()

# ------------------------
# User registration
# ------------------------
def register_user(username, email, password):
    conn = None
    try:
        username = (username or "").strip()
        email = (email or "").strip().lower()
        password = password or ""

        # Basic server-side validations
        if not username or len(username) < 3:
            return {"success": False, "message": "Username must be at least 3 characters"}

        if not email or not is_valid_email(email):
            return {"success": False, "message": "Invalid email format"}

        if not password:
            return {"success": False, "message": "Password cannot be empty"}

        if not is_strong_password(password):
            return {"success": False, "message": "Password too weak"}

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return {"success": False, "message": "Username already exists"}

        cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return {"success": False, "message": "Email already exists"}

        password_hash = hash_password(password)

        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )

        conn.commit()
        return {"success": True, "message": "User registered successfully"}

    except sqlite3.IntegrityError:
        return {"success": False, "message": "Username or email already exists"}

    except Exception as e:
        return {"success": False, "message": f"Database error: {e}"}
    finally:
        if conn:
            conn.close()


def login_user(email, password):
    """
    Authenticate user with email/username and password.
    Implements account lockout after 5 failed attempts.
    Tracks last login timestamp.
    
    Args:
        email (str): User email or username
        password (str): User password
    
    Returns:
        dict: {
            "success": bool,
            "user_id": int (if success),
            "username": str (if success),
            "message": str
        }
    """
    conn = None
    try:
        email = (email or "").strip().lower()
        password = password or ""
        
        if not email or not password:
            return {"success": False, "message": "Email and password are required"}
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Try to find user by email or username
        # First, check which columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if 'is_active' in columns:
            cursor.execute(
                """SELECT user_id, username, email, password_hash, is_active, 
                          failed_login_attempts, locked_until FROM users 
                   WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)""",
                (email, email)
            )
            user = cursor.fetchone()
            if user:
                user_id, username, stored_email, hashed_password, is_active, failed_attempts, locked_until = user
        else:
            cursor.execute(
                """SELECT user_id, username, email, password_hash FROM users 
                   WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)""",
                (email, email)
            )
            user = cursor.fetchone()
            if user:
                user_id, username, stored_email, hashed_password = user
                is_active = 1
                failed_attempts = 0
                locked_until = None
        
        if not user:
            return {"success": False, "message": "Email or username does not exist. Please create an account.", "user_not_found": True}
        
        # Check if account is inactive
        if not is_active:
            return {"success": False, "message": "Account is inactive. Contact support."}
        
        # Check if account is locked
        if locked_until:
            lock_until_dt = datetime.fromisoformat(locked_until)
            if datetime.now() < lock_until_dt:
                remaining_time = (lock_until_dt - datetime.now()).total_seconds() / 60
                return {
                    "success": False,
                    "message": f"Account locked. Try again in {int(remaining_time)} minutes"
                }
            else:
                # Unlock the account if lock time has expired
                cursor.execute(
                    "UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                failed_attempts = 0
        
        # Verify password
        try:
            password_match = bcrypt.checkpw(password.encode(), hashed_password)
        except Exception as e:
            return {"success": False, "message": f"Password verification error: {str(e)}"}
        
        if not password_match:
            # Increment failed login attempts
            new_failed_attempts = failed_attempts + 1
            
            # Lock account if 5 failed attempts
            if new_failed_attempts >= 5:
                locked_until = (datetime.now() + timedelta(minutes=15)).isoformat()
                cursor.execute(
                    """UPDATE users SET failed_login_attempts = ?, locked_until = ? 
                       WHERE user_id = ?""",
                    (new_failed_attempts, locked_until, user_id)
                )
                conn.commit()
                return {
                    "success": False,
                    "message": "Too many failed login attempts. Account locked for 15 minutes."
                }
            else:
                cursor.execute(
                    "UPDATE users SET failed_login_attempts = ? WHERE user_id = ?",
                    (new_failed_attempts, user_id)
                )
                conn.commit()
                attempts_left = 5 - new_failed_attempts
                return {
                    "success": False,
                    "message": f"Incorrect password. {attempts_left} attempts remaining."
                }
        
        # Login successful - update last login and reset failed attempts
        last_login = datetime.now().isoformat()
        cursor.execute(
            """UPDATE users SET last_login = ?, failed_login_attempts = 0, locked_until = NULL 
               WHERE user_id = ?""",
            (last_login, user_id)
        )
        conn.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "username": username,
            "email": stored_email,
            "last_login": last_login,
            "message": "Login successful"
        }
    
    except sqlite3.Error as e:
        return {"success": False, "message": f"Database error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"An error occurred: {str(e)}"}
    finally:
        if conn:
            conn.close()


def generate_reset_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def send_reset_email(email: str, token: str):
    """Send reset link via email (mock example)"""
    reset_link = f"http://example.com/reset_password?token={token}"
    print(f"Sending password reset link to {email}: {reset_link}")
    # In real apps, use SMTP or an email service

def forgot_password(email: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if not user:
            return {"success": False, "message": "Email not found"}
        
        token = generate_reset_token()
        send_reset_email(email, token)
        return {"success": True, "message": "Password reset link sent to your email"}
    
    except sqlite3.Error as e:
        return {"success": False, "message": f"Database error: {str(e)}"}

def delete_user(user_id):
    """
    Delete a user account and all associated data.
    
    Args:
        user_id (int): The user ID to delete
    
    Returns:
        dict: {"success": bool, "message": str}
    """
    conn = None
    try:
        if not user_id:
            return {"success": False, "message": "User ID is required"}
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete the user record
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        # Note: If there are other tables with foreign keys to users,
        # delete those records as well
        
        conn.commit()
        return {"success": True, "message": "Account deleted successfully"}
    
    except sqlite3.Error as e:
        return {"success": False, "message": f"Database error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"An error occurred: {str(e)}"}
    finally:
        if conn:
            conn.close()
