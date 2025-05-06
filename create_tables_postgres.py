from db import get_connection

def create_tables():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE,
            newsletter_optin INTEGER DEFAULT 0
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            service TEXT NOT NULL,
            date DATE NOT NULL,  -- Cambiato da TEXT a DATE
            time TEXT NOT NULL,
            barber TEXT DEFAULT 'Mattia',
            tipo TEXT DEFAULT 'barbiere'
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        """)

        conn.commit()
        conn.close()
        print("✅ Tabelle create con successo.")
    except Exception as e:
        print(f"❌ Errore durante la creazione delle tabelle: {e}")

if __name__ == '__main__':
    create_tables()
