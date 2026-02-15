import os
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from backend.user_management import hash_password, login_user


class LoginAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="vivido_auth_tests_")
        self.db_path = os.path.join(self.tmpdir, "test_auth.db")
        self._create_schema()
        self.get_conn_patcher = patch(
            "backend.user_management.get_connection",
            side_effect=self._get_connection,
        )
        self.get_conn_patcher.start()

    def tearDown(self):
        self.get_conn_patcher.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_schema(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
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
            """
        )
        conn.commit()
        conn.close()

    def _create_user(
        self,
        username,
        email,
        password,
        is_active=1,
        failed_login_attempts=0,
        locked_until=None,
        last_login=None,
    ):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users
            (username, email, password_hash, is_active, failed_login_attempts, locked_until, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                email,
                hash_password(password),
                is_active,
                failed_login_attempts,
                locked_until,
                last_login,
            ),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return user_id

    def _fetch_user(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id, username, email, last_login, is_active, failed_login_attempts, locked_until
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row

    def test_login_success_with_email_updates_last_login_and_resets_failures(self):
        user_id = self._create_user(
            "alice",
            "alice@example.com",
            "Passw0rd!",
            failed_login_attempts=3,
            locked_until=None,
        )

        result = login_user("alice@example.com", "Passw0rd!")

        self.assertTrue(result["success"])
        self.assertEqual(result["user_id"], user_id)
        self.assertEqual(result["username"], "alice")
        self.assertEqual(result["email"], "alice@example.com")
        self.assertIsNotNone(result.get("last_login"))

        row = self._fetch_user(user_id)
        self.assertIsNotNone(row[3])  # last_login
        self.assertEqual(row[5], 0)  # failed_login_attempts
        self.assertIsNone(row[6])  # locked_until

    def test_login_success_with_username_case_insensitive(self):
        self._create_user("BobUser", "bob@example.com", "Passw0rd!")

        result = login_user("bobuser", "Passw0rd!")

        self.assertTrue(result["success"])
        self.assertEqual(result["username"], "BobUser")
        self.assertEqual(result["email"], "bob@example.com")

    def test_non_existent_user_returns_user_not_found(self):
        result = login_user("noone@example.com", "Passw0rd!")

        self.assertFalse(result["success"])
        self.assertTrue(result.get("user_not_found"))
        self.assertIn("does not exist", result["message"])

    def test_inactive_account_is_rejected(self):
        self._create_user("charlie", "charlie@example.com", "Passw0rd!", is_active=0)

        result = login_user("charlie@example.com", "Passw0rd!")

        self.assertFalse(result["success"])
        self.assertIn("inactive", result["message"].lower())

    def test_failed_password_attempts_increment_and_lock_on_fifth_attempt(self):
        user_id = self._create_user("diana", "diana@example.com", "Passw0rd!")

        for expected_left in [4, 3, 2, 1]:
            result = login_user("diana@example.com", "WrongPass1!")
            self.assertFalse(result["success"])
            self.assertIn(f"{expected_left} attempts remaining", result["message"])

        result = login_user("diana@example.com", "WrongPass1!")
        self.assertFalse(result["success"])
        self.assertIn("locked for 15 minutes", result["message"])

        row = self._fetch_user(user_id)
        self.assertEqual(row[5], 5)
        self.assertIsNotNone(row[6])

    def test_locked_account_rejects_even_with_correct_password(self):
        lock_until = (datetime.now() + timedelta(minutes=10)).isoformat()
        self._create_user(
            "eve",
            "eve@example.com",
            "Passw0rd!",
            failed_login_attempts=5,
            locked_until=lock_until,
        )

        result = login_user("eve@example.com", "Passw0rd!")

        self.assertFalse(result["success"])
        self.assertIn("account locked", result["message"].lower())

    def test_expired_lock_is_cleared_and_login_succeeds(self):
        user_id = self._create_user(
            "frank",
            "frank@example.com",
            "Passw0rd!",
            failed_login_attempts=5,
            locked_until=(datetime.now() - timedelta(minutes=1)).isoformat(),
        )

        result = login_user("frank@example.com", "Passw0rd!")

        self.assertTrue(result["success"])
        row = self._fetch_user(user_id)
        self.assertEqual(row[5], 0)
        self.assertIsNone(row[6])

    def test_empty_credentials_are_rejected(self):
        result = login_user("", "")
        self.assertFalse(result["success"])
        self.assertIn("required", result["message"].lower())


if __name__ == "__main__":
    unittest.main()
