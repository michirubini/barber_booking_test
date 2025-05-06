import bcrypt
import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="barberdb",
        user="postgres",
        password="admin",
        host="localhost",
        port="5432"
    )

def create_admin():
    username = input("👤 Inserisci username admin: ").strip()
    password = input("🔐 Inserisci password: ").strip()

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO admins (username, password) VALUES (%s, %s)", (username, hashed))
        conn.commit()
        print("✅ Admin creato con successo!")
    except Exception as e:
        print("❌ Errore durante la creazione dell'admin:", e)

    conn.close()

if __name__ == '__main__':
    create_admin()
