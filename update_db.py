import psycopg2

def column_exists(cursor, table_name, column_name):
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name=%s AND column_name=%s
        )
    """, (table_name, column_name))
    return cursor.fetchone()[0]

def main():
    conn = psycopg2.connect(
        dbname="barberdb",
        user="postgres",
        password="admin",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    # === TABELLA USERS ===
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        print("[OK] Tabella 'users' creata o già esistente")
    except Exception as e:
        print("[ERRORE] Tabella 'users':", e)

    # Colonne users aggiuntive
    extra_user_columns = [
        ("name", "TEXT NOT NULL DEFAULT 'NOME'"),
        ("surname", "TEXT NOT NULL DEFAULT 'COGNOME'"),
        ("phone", "TEXT NOT NULL DEFAULT '0000000000'"),
        ("email", "TEXT UNIQUE"),
        ("newsletter_optin", "INTEGER DEFAULT 0")
    ]
    for col, definition in extra_user_columns:
        if not column_exists(cursor, 'users', col):
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            print(f"[OK] Colonna '{col}' aggiunta a 'users'")
        else:
            print(f"[INFO] La colonna '{col}' esiste già in 'users'")

    # === TABELLA APPOINTMENTS ===
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        print("[OK] Tabella 'appointments' creata o già esistente")
    except Exception as e:
        print("[ERRORE] Tabella 'appointments':", e)

    # Colonne appointments extra
    extra_appointments = [
        ("barber", "TEXT DEFAULT 'Mattia'"),
        ("tipo", "TEXT DEFAULT 'barbiere'")
    ]
    for col, definition in extra_appointments:
        if not column_exists(cursor, 'appointments', col):
            cursor.execute(f"ALTER TABLE appointments ADD COLUMN {col} {definition}")
            print(f"[OK] Colonna '{col}' aggiunta a 'appointments'")
        else:
            print(f"[INFO] La colonna '{col}' esiste già in 'appointments'")

    # === TABELLA PASSWORD TOKENS ===
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        print("[OK] Tabella 'password_tokens' creata o già esistente")
    except Exception as e:
        print("[ERRORE] Tabella 'password_tokens':", e)

    # === TABELLA ADMINS ===
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        print("[OK] Tabella 'admins' creata o già esistente")
    except Exception as e:
        print("[ERRORE] Tabella 'admins':", e)

    # Salva e chiudi
    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Database aggiornato con successo!")

if __name__ == "__main__":
    main()
