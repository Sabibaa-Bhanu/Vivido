"""
Comprehensive test cases for user login authentication system.
Tests cover valid credentials, invalid credentials, account lockout, and edge cases.
"""

import unittest
import sqlite3
import os
import tempfile
from datetime import datetime, timedelta
from backend.user_management import register_user, login_user
from backend.database import get_connection, create_tables


class TestLoginAuthentication(unittest.TestCase):
    """Test cases for login authentication system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database before running tests"""
        # Create temporary database for testing
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_vivido.db")
        
        # Override database path for testing
        import backend.database as db_module
        db_module.DB_PATH = cls.db_path
        
        # Initialize database
        create_tables()
    
    def setUp(self):
        """Clear the users table before each test"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database after all tests"""
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
        os.rmdir(cls.temp_dir)
    
    # ===== Valid Login Tests =====
    
    def test_login_with_valid_credentials(self):
        """Test successful login with valid email and password"""
        # Register user
        reg_result = register_user("testuser", "test@example.com", "ValidPass123!")
        self.assertTrue(reg_result["success"], "Registration should succeed")
        
        # Login with correct credentials
        login_result = login_user("test@example.com", "ValidPass123!")
        self.assertTrue(login_result["success"], "Login should succeed with valid credentials")
        self.assertEqual(login_result["username"], "testuser")
        self.assertIn("user_id", login_result)
    
    def test_login_with_valid_username(self):
        """Test login using username instead of email"""
        # Register user
        reg_result = register_user("testuser", "test@example.com", "ValidPass123!")
        self.assertTrue(reg_result["success"])
        
        # Login with username
        login_result = login_user("testuser", "ValidPass123!")
        self.assertTrue(login_result["success"], "Login should work with username")
        self.assertEqual(login_result["username"], "testuser")
    
    def test_last_login_timestamp_updated(self):
        """Test that last_login timestamp is updated on successful login"""
        # Register user
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Login
        login_user("test@example.com", "ValidPass123!")
        
        # Check database for last_login
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT last_login FROM users WHERE username = ?", ("testuser",))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result[0], "last_login should be set")
        # Verify it's a recent timestamp (within last minute)
        last_login = datetime.fromisoformat(result[0])
        time_diff = (datetime.now() - last_login).total_seconds()
        self.assertLess(time_diff, 60, "last_login should be recent")
    
    def test_failed_attempts_reset_on_successful_login(self):
        """Test that failed_login_attempts counter resets after successful login"""
        # Register user
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Make some failed login attempts
        login_user("test@example.com", "WrongPassword1!")
        login_user("test@example.com", "WrongPassword2!")
        
        # Verify failed attempts counter increased
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT failed_login_attempts FROM users WHERE username = ?", ("testuser",))
        failed_attempts = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(failed_attempts, 2, "Failed attempts should be 2")
        
        # Now login with correct password
        login_result = login_user("test@example.com", "ValidPass123!")
        self.assertTrue(login_result["success"])
        
        # Verify failed attempts reset to 0
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT failed_login_attempts FROM users WHERE username = ?", ("testuser",))
        failed_attempts = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(failed_attempts, 0, "Failed attempts should reset to 0")
    
    # ===== Invalid Credentials Tests =====
    
    def test_login_with_wrong_password(self):
        """Test login rejection with incorrect password"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        login_result = login_user("test@example.com", "WrongPassword123!")
        self.assertFalse(login_result["success"], "Login should fail with wrong password")
        self.assertIn("Incorrect password", login_result["message"])
        self.assertIn("attempts remaining", login_result["message"])
    
    def test_login_with_nonexistent_email(self):
        """Test login rejection for non-existent email"""
        login_result = login_user("nonexistent@example.com", "SomePassword123!")
        self.assertFalse(login_result["success"])
        self.assertIn("Invalid email or username", login_result["message"])
    
    def test_login_with_empty_credentials(self):
        """Test login rejection with empty email/password"""
        login_result = login_user("", "")
        self.assertFalse(login_result["success"])
        self.assertIn("required", login_result["message"].lower())
        
        login_result = login_user("test@example.com", "")
        self.assertFalse(login_result["success"])
        self.assertIn("required", login_result["message"].lower())
    
    # ===== Account Lockout Tests =====
    
    def test_account_lockout_after_5_failed_attempts(self):
        """Test account lockout after 5 consecutive failed login attempts"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Make 5 failed login attempts
        for i in range(5):
            result = login_user("test@example.com", f"WrongPassword{i}!")
            self.assertFalse(result["success"])
        
        # On 5th attempt, account should be locked
        result = login_user("test@example.com", "ValidPass123!")
        self.assertFalse(result["success"])
        self.assertIn("locked", result["message"].lower())
    
    def test_login_blocked_when_account_locked(self):
        """Test that login is blocked even with correct password when account is locked"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Make 5 failed attempts to lock account
        for i in range(5):
            login_user("test@example.com", f"WrongPassword{i}!")
        
        # Try to login with correct password - should still fail
        result = login_user("test@example.com", "ValidPass123!")
        self.assertFalse(result["success"])
        self.assertIn("locked", result["message"].lower())
    
    def test_account_unlock_after_15_minutes(self):
        """Test that account is automatically unlocked after 15 minutes"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Make 5 failed attempts to lock account
        for i in range(5):
            login_user("test@example.com", f"WrongPassword{i}!")
        
        # Manually set locked_until to past time in database
        conn = get_connection()
        cursor = conn.cursor()
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        cursor.execute(
            "UPDATE users SET locked_until = ? WHERE username = ?",
            (past_time, "testuser")
        )
        conn.commit()
        conn.close()
        
        # Try login with correct password - should succeed
        result = login_user("test@example.com", "ValidPass123!")
        self.assertTrue(result["success"], "Login should succeed after lock expires")
    
    def test_lockout_message_shows_remaining_time(self):
        """Test that lockout message shows remaining time"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Make 5 failed attempts
        for i in range(5):
            login_user("test@example.com", f"WrongPassword{i}!")
        
        # Try to login - should show lockout message with time
        result = login_user("test@example.com", "ValidPass123!")
        self.assertFalse(result["success"])
        self.assertIn("minutes", result["message"].lower())
    
    def test_failed_attempts_counter_increments(self):
        """Test that failed_login_attempts counter increments correctly"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        for attempt in range(1, 5):
            login_user("test@example.com", f"WrongPassword{attempt}!")
            
            cursor.execute("SELECT failed_login_attempts FROM users WHERE username = ?", ("testuser",))
            failed_count = cursor.fetchone()[0]
            self.assertEqual(failed_count, attempt, f"Failed attempts should be {attempt}")
        
        conn.close()
    
    # ===== Account Status Tests =====
    
    def test_login_blocked_for_inactive_account(self):
        """Test that login is blocked for inactive accounts"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Deactivate account
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 0 WHERE username = ?", ("testuser",))
        conn.commit()
        conn.close()
        
        # Try to login
        result = login_user("test@example.com", "ValidPass123!")
        self.assertFalse(result["success"])
        self.assertIn("inactive", result["message"].lower())
    
    # ===== Edge Cases =====
    
    def test_email_case_insensitive_login(self):
        """Test that email login is case-insensitive"""
        register_user("testuser", "Test@Example.COM", "ValidPass123!")
        
        # Login with different case
        result = login_user("test@example.com", "ValidPass123!")
        self.assertTrue(result["success"], "Email should be case-insensitive")
    
    def test_multiple_failed_attempts_show_decreasing_chances(self):
        """Test that user sees decreasing attempts remaining"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        expected_remaining = [4, 3, 2, 1]
        
        for i, expected in enumerate(expected_remaining, 1):
            result = login_user("test@example.com", f"WrongPassword{i}!")
            self.assertFalse(result["success"])
            # Extract number from message like "4 attempts remaining"
            self.assertIn(str(expected), result["message"])
    
    def test_login_with_spaces_in_email(self):
        """Test that login trims whitespace from email"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Login with spaces around email
        result = login_user("  test@example.com  ", "ValidPass123!")
        self.assertTrue(result["success"], "Login should trim email spaces")
    
    def test_password_case_sensitive(self):
        """Test that passwords are case-sensitive"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        # Try with different case
        result = login_user("test@example.com", "validpass123!")
        self.assertFalse(result["success"], "Password should be case-sensitive")
    
    def test_login_returns_all_required_fields(self):
        """Test that successful login returns all required fields"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        result = login_user("test@example.com", "ValidPass123!")
        self.assertTrue(result["success"])
        self.assertIn("user_id", result)
        self.assertIn("username", result)
        self.assertIn("email", result)
        self.assertIn("message", result)
    
    def test_multiple_users_independent_lockout(self):
        """Test that account lockout is independent for each user"""
        # Register two users
        register_user("user1", "user1@example.com", "ValidPass123!")
        register_user("user2", "user2@example.com", "ValidPass123!")
        
        # Lock user1 with 5 failed attempts
        for i in range(5):
            login_user("user1@example.com", f"WrongPassword{i}!")
        
        # User1 should be locked
        result1 = login_user("user1@example.com", "ValidPass123!")
        self.assertFalse(result1["success"])
        self.assertIn("locked", result1["message"].lower())
        
        # User2 should still be able to login with correct password
        result2 = login_user("user2@example.com", "ValidPass123!")
        self.assertTrue(result2["success"], "User2 should not be affected by User1 lockout")


class TestSessionManagement(unittest.TestCase):
    """Test cases for session management using Streamlit session state"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_vivido.db")
        
        import backend.database as db_module
        db_module.DB_PATH = cls.db_path
        
        create_tables()
    
    def setUp(self):
        """Clear users table before each test"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
        os.rmdir(cls.temp_dir)
    
    def test_session_state_structure_on_successful_login(self):
        """Test the structure of session state that should be set on successful login"""
        register_user("testuser", "test@example.com", "ValidPass123!")
        
        result = login_user("test@example.com", "ValidPass123!")
        
        # Verify result contains information needed for session state
        self.assertTrue(result["success"])
        self.assertIn("user_id", result)
        self.assertIn("username", result)
        self.assertIn("email", result)
        
        # These should be used to populate session state as:
        # st.session_state["logged_in"] = True
        # st.session_state["current_user"] = result["email"]
        # st.session_state["current_username"] = result["username"]
        # st.session_state["user_id"] = result["user_id"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
