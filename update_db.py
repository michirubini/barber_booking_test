import sqlite3

# Connessione al database
conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

# Aggiunta colonne alla tabella users se non esistono
try:
    cursor.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT 'NOME'")
    print("[OK] Colonna 'name' aggiunta")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'name' esiste già")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN surname TEXT NOT NULL DEFAULT 'COGNOME'")
    print("[OK] Colonna 'surname' aggiunta")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'surname' esiste già")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT '0000000000'")
    print("[OK] Colonna 'phone' aggiunta")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'phone' esiste già")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
    print("[OK] Colonna 'email' aggiunta con vincolo UNIQUE")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'email' esiste già")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN newsletter_optin INTEGER DEFAULT 0")
    print("[OK] Colonna 'newsletter_optin' aggiunta")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'newsletter_optin' esiste già")

# Aggiunta colonna 'barber' nella tabella appointments
try:
    cursor.execute("ALTER TABLE appointments ADD COLUMN barber TEXT DEFAULT 'Mattia'")
    print("[OK] Colonna 'barber' aggiunta alla tabella appointments")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'barber' esiste già nella tabella appointments")

# Aggiunta colonna 'tipo' nella tabella appointments
try:
    cursor.execute("ALTER TABLE appointments ADD COLUMN tipo TEXT DEFAULT 'barbiere'")
    print("[OK] Colonna 'tipo' aggiunta alla tabella appointments")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'tipo' esiste già nella tabella appointments")

# ✅ Aggiunta tabella per token reset password
try:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS password_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL,
        expires_at DATETIME NOT NULL,
        used INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    print("[OK] Tabella 'password_tokens' creata o già esistente")
except Exception as e:
    print(f"[ERRORE] Creazione tabella token: {e}")

# Salvataggio e chiusura
conn.commit()
conn.close()
print("\n✅ Database aggiornato con successo!")
