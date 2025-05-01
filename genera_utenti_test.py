import psycopg2
import random

# Connessione al database PostgreSQL
conn = psycopg2.connect(
    dbname="barber_booking",
    user="postgres",
    password="admin",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

nomi = ["Luca", "Anna", "Marco", "Elena", "Giulia", "Davide", "Sara", "Paolo", "Chiara", "Matteo"]
cognomi = ["Rossi", "Bianchi", "Verdi", "Conti", "Esposito", "Neri", "Romano", "Ferrari", "Moretti", "Gallo"]

inseriti = 0

for i in range(1, 101):
    name = random.choice(nomi)
    surname = random.choice(cognomi)
    phone = f"333000{i:03d}"
    email = f"test{i}@example.com"
    username = f"testuser{i}"
    password = "testpass"  # Puoi anche criptarla con bcrypt se necessario
    newsletter = 1

    try:
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email, newsletter_optin)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, password, name, surname, phone, email, newsletter))
        inseriti += 1
    except Exception as e:
        print(f"⚠️ Errore con {username}: {e}")

conn.commit()
conn.close()
print(f"✅ Inseriti {inseriti} utenti con newsletter attiva.")
