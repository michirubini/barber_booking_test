import psycopg2

conn = psycopg2.connect(
    dbname="barber_booking",
    user="postgres",
    password="admin",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Rimuove gli utenti finti con username/email tipici
cursor.execute("""
    DELETE FROM users
    WHERE username LIKE 'testuser%' OR email LIKE 'test%@example.com'
""")
deleted = cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Utenti fake eliminati: {deleted}")
