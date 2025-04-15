import sqlite3

conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

# Elimina gli appuntamenti collegati a utenti finti (se ci fossero)
cursor.execute("""
    DELETE FROM appointments
    WHERE user_id IN (
        SELECT id FROM users WHERE username LIKE 'testuser%'
    )
""")

# Elimina gli utenti finti
cursor.execute("DELETE FROM users WHERE username LIKE 'testuser%'")

conn.commit()
conn.close()
print("🧼 Utenti test eliminati.")
