import psycopg2

conn = psycopg2.connect(
    dbname="barber_booking",
    user="postgres",
    password="admin",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Elimina prima gli appuntamenti legati agli utenti fake
cursor.execute("""
    DELETE FROM appointments
    WHERE user_id IN (
        SELECT id FROM users WHERE username LIKE 'testuser%' OR email LIKE 'test%@example.com'
    )
""")
deleted_appointments = cursor.rowcount

# Ora elimina gli utenti fake
cursor.execute("""
    DELETE FROM users
    WHERE username LIKE 'testuser%' OR email LIKE 'test%@example.com'
""")
deleted_users = cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Appuntamenti fake eliminati: {deleted_appointments}")
print(f"✅ Utenti fake eliminati: {deleted_users}")
