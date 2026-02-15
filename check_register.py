from backend.database import get_connection, create_tables
from backend.user_management import register_user

create_tables()
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT username, email FROM users")
print('Current users:')
for r in cur.fetchall():
    print(r)

print('Attempt register validuser:')
print(register_user('validuser','validuser@gmail.com','Strong@123'))

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT username, email FROM users WHERE username=?", ('validuser',))
print('After attempt:')
for r in cur.fetchall():
    print(r)
