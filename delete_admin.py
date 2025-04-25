import psycopg2

# === CONFIGURAZIONE DB ===
DB_NAME = "barberdb"
DB_USER = "postgres"
DB_PASSWORD = "admin"
DB_HOST = "localhost"
DB_PORT = "5432"

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def delete_admin():
    print("⚠️  Elimina un amministratore")

    username = input("Inserisci l'username dell'admin da eliminare: ").strip()

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verifica se l'admin esiste
        cursor.execute("SELECT id FROM admins WHERE username = %s", (username,))
        result = cursor.fetchone()

        if not result:
            print(f"❌ Admin '{username}' non trovato.")
        else:
            confirm = input(f"Sei sicuro di voler eliminare l'admin '{username}'? (s/N): ").strip().lower()
            if confirm == 's':
                cursor.execute("DELETE FROM admins WHERE username = %s", (username,))
                conn.commit()
                print(f"✅ Admin '{username}' eliminato con successo.")
            else:
                print("⛔️ Operazione annullata.")

        conn.close()

    except Exception as e:
        print("❌ Errore durante l'eliminazione:", e)

if __name__ == "__main__":
    delete_admin()
