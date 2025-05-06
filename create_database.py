import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    # Connessione al server PostgreSQL (ma non a un db specifico)
    conn = psycopg2.connect(
        dbname='barberdb',
        user='postgres',
        password='admin',
        host='localhost'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Crea il database se non esiste
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='barberdb'")
    exists = cursor.fetchone()
    if not exists:
        cursor.execute('CREATE DATABASE barberdb')
        print("✅ Database 'barberdb' creato con successo.")
    else:
        print("ℹ️ Il database 'barberdb' esiste già.")

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Errore durante la creazione del database:", e)
