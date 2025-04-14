import sqlite3
import random

conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

nomi = ["Luca", "Anna", "Marco", "Elena", "Giulia", "Davide", "Sara", "Paolo", "Chiara", "Matteo"]
cognomi = ["Rossi", "Bianchi", "Verdi", "Conti", "Esposito", "Neri", "Romano", "Ferrari", "Moretti", "Gallo"]

for i in range(1, 101):  # 🔁 100 utenti
    name = random.choice(nomi)
    surname = random.choice(cognomi)
    phone = f"333000{i:03d}"
    email = f"test{i}@example.com"
    username = f"testuser{i}"
    password = "testpass"
    newsletter = 1

    try:
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email, newsletter_optin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, password, name, surname, phone, email, newsletter))
    except Exception as e:
        print(f"⚠️ Errore con {username}: {e}")

conn.commit()
conn.close()
print("✅ 100 utenti test inseriti.")

