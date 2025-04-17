import sqlite3

username = input("🔴 Inserisci l'username dell'admin da eliminare: ")

conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
admin = cursor.fetchone()

if admin:
    cursor.execute("DELETE FROM admins WHERE username = ?", (username,))
    conn.commit()
    print(f"✅ Admin '{username}' eliminato con successo.")
else:
    print("⚠️ Admin non trovato.")

conn.close()
