# Authentication System Documentation

## Overview
The Vivido authentication system provides secure user login with advanced security features including account lockout, failed attempt tracking, and session management.

## Features

### 1. **Secure Password Verification**
- Uses bcrypt hashing for password storage and verification
- Passwords are never stored in plain text
- Cryptographic comparison prevents timing attacks

### 2. **Account Lockout Protection**
- Automatic account lockout after 5 failed login attempts
- 15-minute lockout period prevents brute force attacks
- Lockout timer automatically expires after specified duration
- Users receive clear messaging about remaining lockout time

### 3. **Failed Login Attempt Tracking**
- Counts consecutive failed login attempts
- Shows remaining attempts to users (5, 4, 3, 2, 1)
- Counter resets to 0 on successful login
- Counter resets to 0 when lockout timer expires

### 4. **Login Timestamp Tracking**
- Records exact timestamp of each successful login
- Stored in ISO format for easy parsing
- Useful for security audits and user activity tracking

### 5. **Account Status Management**
- Support for active/inactive account status
- Inactive accounts blocked from login
- Database field: `is_active` (1 = active, 0 = inactive)

### 6. **Flexible Login Method**
- Users can login with either email OR username
- Email comparison is case-insensitive
- Whitespace automatically trimmed

### 7. **Session Management Integration**
- Streamlit session state for persistent user sessions
- Stores: `logged_in`, `current_user`, `current_username`, `user_id`
- Auto-clears on logout

## Database Schema

### Users Table
```sql
CREATE TABLE users (
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
```

### New Fields Added
- `is_active`: Boolean flag (1=active, 0=inactive)
- `failed_login_attempts`: Counter for failed attempts (0-5)
- `locked_until`: ISO timestamp when account lockout expires

## API Reference

### `login_user(email, password)`

Authenticates a user and manages account security.

**Parameters:**
- `email` (str): User's email address or username
- `password` (str): User's password

**Returns:**
```python
{
    "success": bool,           # True if login successful
    "user_id": int,            # User ID (if success)
    "username": str,           # Username (if success)
    "email": str,              # Email address (if success)
    "message": str             # Status message
}
```

**Success Response:**
```python
{
    "success": True,
    "user_id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "message": "Login successful"
}
```

**Failure Response Examples:**

Invalid credentials:
```python
{
    "success": False,
    "message": "Invalid email or username"
}
```

Wrong password (with attempts shown):
```python
{
    "success": False,
    "message": "Incorrect password. 4 attempts remaining."
}
```

Account locked:
```python
{
    "success": False,
    "message": "Account locked. Try again in 14 minutes"
}
```

Inactive account:
```python
{
    "success": False,
    "message": "Account is inactive. Contact support."
}
```

## Security Features

### 1. **Brute Force Protection**
```
Attempt 1: ✓ Failed - "4 attempts remaining"
Attempt 2: ✓ Failed - "3 attempts remaining"
Attempt 3: ✓ Failed - "2 attempts remaining"
Attempt 4: ✓ Failed - "1 attempt remaining"
Attempt 5: ✗ LOCKED - "Account locked for 15 minutes"
```

### 2. **Password Security**
- Bcrypt with salt for hashing
- Automatic verification without exposing hash
- 12-round bcrypt (configurable)

### 3. **Account Protection**
- Account lockout prevents unauthorized access
- Failed attempt counter is independent per user
- Multiple users don't affect each other

### 4. **Session Security**
- Streamlit session state for secure session handling
- Session data not exposed in URLs
- Auto-clears on page refresh (if needed)

## Usage Examples

### Basic Login
```python
from backend.user_management import login_user

result = login_user("user@example.com", "Password123!")

if result["success"]:
    st.session_state["logged_in"] = True
    st.session_state["current_user"] = result["email"]
    st.session_state["user_id"] = result["user_id"]
    st.success("Logged in successfully!")
else:
    st.error(result["message"])
```

### Login with Username
```python
result = login_user("john_doe", "Password123!")
```

### Handling Account Lockout
```python
result = login_user("user@example.com", "wrong_password")

if "locked" in result["message"].lower():
    st.warning(result["message"])
    # Show "Try again later" message
elif "attempts remaining" in result["message"]:
    st.info(result["message"])
    # Show warning about remaining attempts
```

## Testing

### Run All Tests
```bash
python -m pytest test_login.py -v
```

### Run Specific Test Class
```bash
python -m pytest test_login.py::TestLoginAuthentication -v
```

### Run Specific Test
```bash
python -m pytest test_login.py::TestLoginAuthentication::test_login_with_valid_credentials -v
```

## Test Coverage

The `test_login.py` file includes 20+ comprehensive test cases:

### Valid Login Tests (4)
- ✓ Login with valid email and password
- ✓ Login with valid username
- ✓ Last login timestamp updated
- ✓ Failed attempts reset on successful login

### Invalid Credentials Tests (3)
- ✓ Login with wrong password
- ✓ Login with non-existent email
- ✓ Login with empty credentials

### Account Lockout Tests (5)
- ✓ Account lockout after 5 failed attempts
- ✓ Login blocked when account locked (even with correct password)
- ✓ Account unlock after 15 minutes
- ✓ Lockout message shows remaining time
- ✓ Failed attempts counter increments

### Account Status Tests (1)
- ✓ Login blocked for inactive accounts

### Edge Cases Tests (7)
- ✓ Email case-insensitive login
- ✓ Multiple failed attempts show decreasing chances
- ✓ Login with spaces in email
- ✓ Password case-sensitive
- ✓ Login returns all required fields
- ✓ Multiple users independent lockout
- ✓ Session state structure validation

## Architecture

```
┌─────────────────┐
│   login.py      │ (Streamlit UI)
│   (Page)        │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────┐
│  backend/user_management.py │
│  (login_user function)      │
└────────┬────────────────────┘
         │
         ↓
┌──────────────────────┐
│  backend/database.py │ (SQLite)
│  (User table access) │
└──────────────────────┘
         │
         ↓
┌──────────────────────┐
│  SQLite Database     │
│  (users table)       │
└──────────────────────┘
```

## Error Handling

All error cases are gracefully handled:

| Error | Message | Action |
|-------|---------|--------|
| Empty credentials | "Email and password are required" | Display in UI |
| Invalid email | "Invalid email or username" | Display in UI |
| Wrong password | "Incorrect password. X attempts remaining." | Increment counter |
| Account locked | "Account locked. Try again in X minutes" | Display timer |
| Inactive account | "Account is inactive. Contact support." | Display error |
| DB error | "Database error: [error]" | Log and display generic error |

## Migration Guide

If upgrading from previous version without lockout features:

### 1. Update Database
The `create_tables()` function automatically adds new columns:
- `is_active` (defaults to 1 for existing users)
- `failed_login_attempts` (defaults to 0)
- `locked_until` (defaults to NULL)

### 2. Update Code
Old code:
```python
result = login_user(email, password)
if result["success"]:
    st.session_state["current_user"] = email
```

New code:
```python
result = login_user(email, password)
if result["success"]:
    st.session_state["current_user"] = result["email"]
    st.session_state["user_id"] = result["user_id"]
```

## Performance Considerations

- **Password hashing**: ~100ms per attempt (by design, to slow brute force)
- **Database queries**: Single indexed query by email/username
- **Memory**: Session state minimal (~1KB per user)

## Future Enhancements

Potential features for future versions:
- [ ] Email verification for new accounts
- [ ] Two-factor authentication (2FA)
- [ ] Password reset via email token
- [ ] Login history per user
- [ ] Suspicious activity detection
- [ ] IP-based lockout (block IPs with many attempts)
- [ ] Device fingerprinting
- [ ] Biometric login support

## Support & Troubleshooting

### Issue: Account locked but timer expired
**Solution**: Manual fix in database
```python
import sqlite3
conn = sqlite3.connect("data/vivido.db")
cursor = conn.cursor()
cursor.execute("UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE username = ?", ("username",))
conn.commit()
```

### Issue: Password verification fails
**Solution**: Ensure bcrypt is installed
```bash
pip install bcrypt
```

### Issue: Session state not persisting
**Solution**: Check Streamlit version (requires 1.18+)
```bash
pip install --upgrade streamlit
```

## License
Part of Vivido project - All rights reserved.

## Contact
For security issues, please contact: security@vivido.dev
