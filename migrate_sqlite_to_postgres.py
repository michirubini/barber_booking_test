# migrate_sqlite_to_postgres.py
import sqlite3
import psycopg2
from db import get_connection

print("\n🚀 Avvio migrazione dati da SQLite → PostgreSQL...")

# Connessioni ai database
sqlite_conn = sqlite3.connect("bookings.db")
sqlite_cursor = sqlite_conn.cursor()
pg_conn = get_connection()
pg_cursor = pg_conn.cursor()

# Migra utenti
sqlite_cursor.execute("SELECT id, username, password, name, surname, phone, email, newsletter_optin FROM users")
users = sqlite_cursor.fetchall()
for u in users:
    pg_cursor.execute("""
        INSERT INTO users (id, username, password, name, surname, phone, email, newsletter_optin)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, u)
print(f"✅ Utenti migrati: {len(users)}")

# Migra appuntamenti
sqlite_cursor.execute("SELECT id, user_id, service, date, time, barber, tipo FROM appointments")
appointments = sqlite_cursor.fetchall()
for a in appointments:
    pg_cursor.execute("""
        INSERT INTO appointments (id, user_id, service, date, time, barber, tipo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, a)
print(f"✅ Appuntamenti migrati: {len(appointments)}")

# Migra admin
sqlite_cursor.execute("SELECT id, username, password FROM admins")
admins = sqlite_cursor.fetchall()
for a in admins:
    pg_cursor.execute("""
        INSERT INTO admins (id, username, password)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, a)
print(f"✅ Admin migrati: {len(admins)}")

# Migra token reset
sqlite_cursor.execute("SELECT id, user_id, token, expires_at, used FROM password_tokens")
tokens = sqlite_cursor.fetchall()
ignorati = 0
for t in tokens:
    try:
        pg_cursor.execute("""
            INSERT INTO password_tokens (id, user_id, token, expires_at, used)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, t)
    except psycopg2.errors.ForeignKeyViolation:
        print(f"⚠️  Token ignorato: utente {t[1]} non esiste in PostgreSQL.")
        pg_conn.rollback()
        ignorati += 1
print(f"✅ Token reset migrati: {len(tokens) - ignorati} (⚠️ ignorati: {ignorati})")

pg_conn.commit()
pg_conn.close()
sqlite_conn.close()

print("\n🎉 Migrazione completata con successo!")
