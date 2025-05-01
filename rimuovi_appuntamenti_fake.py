import psycopg2

conn = psycopg2.connect(
    dbname="barber_booking",
    user="postgres",
    password="admin",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Rimuove appuntamenti legati a utenti finti (username che iniziano per "testuser")
cursor.execute("""
    DELETE FROM appointments
    WHERE user_id IN (
        SELECT id FROM users WHERE username LIKE 'testuser%'
    )
""")
deleted = cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Appuntamenti fake eliminati: {deleted}")
