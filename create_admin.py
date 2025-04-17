import sqlite3
import bcrypt

# Inserimento dati
username = input("👤 Inserisci username admin: ")
password = input("🔐 Inserisci password: ")

# Hash password
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Connessione DB
conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

# Crea tabella se non esiste (sicurezza)
cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Controlla se admin già esiste
cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
if cursor.fetchone():
    print(f"⚠️ L'admin '{username}' esiste già.")
else:
    cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    print(f"✅ Admin '{username}' creato con successo!")

conn.close()
