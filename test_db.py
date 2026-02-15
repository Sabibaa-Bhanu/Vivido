

# test_db.py
from backend.database import create_tables, get_connection

# ========================
# Insert sample data
# ========================
def insert_sample_data():
    conn = get_connection()
    cursor = conn.cursor()

    # Users
    cursor.execute("INSERT OR IGNORE INTO users (username, email, password_hash) VALUES ('john_doe','john@example.com','hashed_password1')")
    cursor.execute("INSERT OR IGNORE INTO users (username, email, password_hash) VALUES ('jane_smith','jane@example.com','hashed_password2')")

    # Transactions
    cursor.execute("INSERT OR IGNORE INTO transactions (user_id, amount, payment_status, payment_method) VALUES (1, 150.00, 'PENDING', 'CREDIT_CARD')")
    cursor.execute("INSERT OR IGNORE INTO transactions (user_id, amount, payment_status, payment_method) VALUES (2, 200.50, 'SUCCESS', 'UPI')")

    # Image history
    cursor.execute("INSERT OR IGNORE INTO image_history (user_id, original_image_path, processed_image_path, style_applied) VALUES (1, 'uploads/img1.jpg', 'processed/img1_cartoon.jpg', 'Cartoon')")
    cursor.execute("INSERT OR IGNORE INTO image_history (user_id, original_image_path, processed_image_path, style_applied) VALUES (2, 'uploads/img2.jpg', 'processed/img2_oil.jpg', 'Oil Painting')")

    conn.commit()
    return conn, cursor

# ========================
# Fetch & print data
# ========================
def fetch_data(conn, cursor):
    print("\n--- USERS ---")
    cursor.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        print(row)

    print("\n--- TRANSACTIONS ---")
    cursor.execute("SELECT * FROM transactions")
    for row in cursor.fetchall():
        print(row)

    print("\n--- IMAGE HISTORY ---")
    cursor.execute("SELECT * FROM image_history")
    for row in cursor.fetchall():
        print(row)

    conn.close()

# ========================
# Main
# ========================
if __name__ == "__main__":
    create_tables()  # ✅ Use database.py
    conn, cursor = insert_sample_data()
    fetch_data(conn, cursor)
