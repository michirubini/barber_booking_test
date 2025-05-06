from flask import Flask, render_template, request, redirect, url_for, session, jsonify  # type: ignore
from datetime import datetime, timedelta
import bcrypt
import uuid
import re
import os

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Carica automaticamente il file .env.local se esiste, altrimenti usa .env.production (Render)
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv(".env.production")

# Funzione per connettersi al database PostgreSQL con SSL
def get_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            sslmode='prefer'  # Try 'prefer' or 'disable' if 'required' fails
        )
        print("✅ Connessione al database riuscita.")
        return conn
    except Exception as e:
        print(f"❌ Errore nella connessione al database: {e}")
        raise



app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Aggiungi il codice per il resto dell'applicazione Flask (rotte, gestione utenti, ecc.)



# ---------- INIZIALIZZAZIONE DB ----------




app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ---------- INIZIALIZZAZIONE DB ----------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabella utenti
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE,
            newsletter_optin INTEGER DEFAULT 0
        )
    ''')

    # Tabella appuntamenti
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            barber TEXT DEFAULT 'Mattia',
            tipo TEXT DEFAULT 'barbiere',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Tabella admins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Tabella token per reset password
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()




# ---------- ROTTE PRINCIPALI ----------
@app.route('/')
def index():
    return render_template('index.html')

import uuid
from datetime import datetime, timedelta

def is_password_strong(password):
    return (
        len(password) >= 8 and
        re.search(r'[A-Za-z]', password) and
        re.search(r'\d', password) and
        re.search(r'[^A-Za-z0-9]', password)
    )


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    error = None

    if request.method == 'POST':
        email = request.form['email']
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            user_id = user[0]
            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(minutes=30)

            cursor.execute("""
                INSERT INTO password_tokens (user_id, token, expires_at)
                VALUES (%s, %s, %s)
            """, (user_id, token, expires_at))
            conn.commit()

            # 🔗 Link da inviare via email
            reset_link = url_for('reset_password', token=token, _external=True)

            invia_email_reset(email, reset_link)

            message = "Ti abbiamo inviato un'email con il link per reimpostare la password."
        else:
            error = "Email non trovata nel sistema."

        conn.close()

    return render_template('forgot_password.html', message=message, error=error)

def invia_email_reset(email, reset_link):
    import smtplib
    from email.mime.text import MIMEText

    mittente = 'rubinimc@gmail.com'  # ← usa la tua email reale
    password = 'mtgk jhxz wagn wicg'  # ← usa la tua app password (Gmail 2FA)

    msg = MIMEText(f"""\
Ciao!

Abbiamo ricevuto una richiesta per reimpostare la tua password.

🔗 Clicca qui sotto per scegliere una nuova password:
{reset_link}

Il link è valido per 30 minuti.

Se non sei stato tu a fare la richiesta, ignora questa email.
""")

    msg['Subject'] = "🔐 Reimposta la tua password"
    msg['From'] = mittente
    msg['To'] = email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mittente, password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email inviata a {email}")
    except Exception as e:
        print(f"❌ Errore invio email a {email}: {e}")


@app.route('/admin_delete_appointment/<int:appointment_id>', methods=['POST'])
def admin_delete_appointment(appointment_id):
    if 'admin' not in session:
        return '', 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
    conn.commit()
    conn.close()
    return '', 204


@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print(f"🔍 Tentativo login per username: {username}")  # Aggiungi un log per vedere cosa viene inviato

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id, username, password FROM admins WHERE username = %s", (username,))
            admin = cursor.fetchone()
            conn.close()

            if admin:
                print(f"Admin trovato: {admin}")  # Verifica che l'admin sia trovato

            # Se trovato e la password combacia
            if admin and bcrypt.checkpw(password.encode('utf-8'), admin[2].encode('utf-8')):
                session['admin'] = admin[0]
                return redirect(url_for('admin_dashboard'))
            else:
                error = "Credenziali non valide"

        except Exception as e:
            error = f"Errore durante il login: {str(e)}"  # Aggiungi messaggio di errore
            print(f"❌ Errore durante il login: {e}")

    return render_template('login_admin.html', error=error)



@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token')
    error = None
    success = None
    show_form = True

    if not token:
        return "Token mancante", 400

    conn = get_connection()
    cursor = conn.cursor()

    # Verifica token esistente
    cursor.execute("""
        SELECT pt.user_id, pt.expires_at, pt.used
        FROM password_tokens pt
        WHERE pt.token = %s
    """, (token,))
    token_data = cursor.fetchone()

    if not token_data:
        conn.close()
        return render_template("reset_password.html", error="Token non valido.", show_form=False)

    user_id, expires_at, used = token_data  # ✅ ora expires_at è già datetime

    if used:
        conn.close()
        return render_template("reset_password.html", error="Questo link è già stato utilizzato.", show_form=False)
    if datetime.now() > expires_at:
        conn.close()
        return render_template("reset_password.html", error="Il link per reimpostare la password è scaduto.", show_form=False)

    # === POST: aggiorna la password ===
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # 1) checks matching
        if new_password != confirm_password:
            error = "Le password non coincidono."
            return render_template("reset_password.html", error=error, show_form=True)

        # 2) server-side strength check
        if not is_password_strong(new_password):
            error = "La password deve contenere almeno 8 caratteri, una lettera, un numero e un simbolo."
            return render_template("reset_password.html", error=error, show_form=True)

        # 3) aggiorna e marca token come usato
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, user_id))
        cursor.execute("UPDATE password_tokens SET used = 1 WHERE token = %s", (token,))
        conn.commit()
        conn.close()

        success = "✅ La tua password è stata reimpostata con successo!"
        return render_template("reset_password.html", success=success, show_form=False)

    # GET – mostra il form
    conn.close()
    return render_template("reset_password.html", show_form=True)



@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):  # user[2] = password DB
            session['user_id'] = user[0]
            session['name'] = user[3]
            return redirect(url_for('user_dashboard'))
        else:
            error = "Username o password errati"

    return render_template('login_user.html', error=error)



@app.route('/admin_users')
def admin_users():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    search_query = request.args.get('search', '').strip()

    conn = get_connection()
    cursor = conn.cursor()

    if search_query:
        search = f"%{search_query}%"
        cursor.execute("""
            SELECT COUNT(*) FROM users
            WHERE name LIKE %s OR surname LIKE %s OR phone LIKE %s OR email LIKE %s
        """, (search, search, search, search))
        total_users = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, name, surname, phone, email, username
            FROM users
            WHERE name LIKE %s OR surname LIKE %s OR phone LIKE %s OR email LIKE %s
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (search, search, search, search, per_page, offset))
    else:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, name, surname, phone, email, username
            FROM users
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    users = cursor.fetchall()
    conn.close()

    total_pages = (total_users + per_page - 1) // per_page

    return render_template('admin_users.html',
                           users=users,
                           page=page,
                           total_pages=total_pages,
                           search_query=search_query)




@app.route('/admin_delete_selected_users', methods=['POST'])
def delete_selected_users():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    selected_ids = request.form.getlist('selected_users')
    if selected_ids:
        conn = get_connection()
        cursor = conn.cursor()

        # Prima cancella gli appuntamenti legati
        cursor.executemany("DELETE FROM appointments WHERE user_id = %s", [(uid,) for uid in selected_ids])
        # Poi elimina gli utenti
        cursor.executemany("DELETE FROM users WHERE id = %s", [(uid,) for uid in selected_ids])

        conn.commit()
        conn.close()

    return redirect(url_for('admin_users'))

@app.route('/admin_edit_user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # ✅ Newsletter aggiornabile
        newsletter = 1 if request.form.get('newsletter') == 'on' else 0

        # Controlli duplicati
        cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Username già in uso")

        cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Email già registrata")

        # Salva modifiche
        cursor.execute("""
            UPDATE users 
            SET name = %s, surname = %s, phone = %s, email = %s, username = %s, password = %s, newsletter_optin = %s
            WHERE id = %s
        """, (name, surname, phone, email, username, password, newsletter, user_id))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))

    # Carica dati utente (incluso newsletter_optin)
    cursor.execute("SELECT name, surname, phone, email, username, password, newsletter_optin FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return redirect(url_for('admin_users'))

    return render_template('admin_edit_user.html', user=user)


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    return render_template('goodbye.html')




@app.route('/admin_delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM appointments WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_users'))




# ---------- ALTRE FUNZIONI UTILI ----------

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def invia_email_registrazione(destinatario, nome, cognome, username, telefono, password):
    mittente = 'rubinimc@gmail.com'  # o la mail definitiva del salone
    password_email = 'mtgk jhxz wagn wicg'

    oggetto = "Benvenuto da Les Klips Hair & Barber – Registrazione completata"
    messaggio = f"""
Ciao {nome} {cognome},

Grazie per esserti registrato/a presso Les Klips Hair & Barber!
Siamo felici di averti con noi.

Ecco i tuoi dati di accesso personali:

• Username: {username}
• Password: {password}
• Email: {destinatario}
• Telefono: {telefono}

Potrai ora prenotare facilmente i tuoi appuntamenti direttamente online.

Per modifiche o cancellazioni puoi gestire tutto dal sito, oppure chiamare il numero: 051 683 0322 📞

Per qualsiasi altra informazione, siamo a tua disposizione.

A presto,  
Il team Les Klips Hair & Barber
"""


    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = oggetto
    msg.attach(MIMEText(messaggio, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mittente, password_email)
        server.send_message(msg)
        server.quit()
        print("📨 Email inviata con successo!")
    except Exception as e:
        print("❌ Errore nell'invio dell'email:", e)

def invia_email_marketing(destinatario, oggetto, corpo):
    mittente = 'rubinimc@gmail.com'
    password = 'mtgk jhxz wagn wicg'

    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = oggetto
    msg.attach(MIMEText(corpo, 'plain'))

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(mittente, password)
    server.send_message(msg)
    server.quit()



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # ✅ Privacy obbligatoria
        privacy = request.form.get('privacy')
        if not privacy:
            return render_template('register.html', error="È necessario accettare il trattamento dei dati personali.")

        # ✅ Newsletter facoltativa
        newsletter = 1 if request.form.get('newsletter') == 'on' else 0

        # 🔐 Verifica forza password
        import re
        def is_password_strong(pwd):
            return (
                len(pwd) >= 8 and
                re.search(r'[A-Za-z]', pwd) and
                re.search(r'\d', pwd) and
                re.search(r'[^A-Za-z0-9]', pwd)
            )

        if not is_password_strong(password):
            return render_template('register.html', error="La password deve contenere almeno 8 caratteri, una lettera, un numero e un simbolo.")

        # ❌ Controllo se le password coincidono
        if password != confirm_password:
            return render_template('register.html', error="Le password non coincidono.")

        # ✅ Hash password con bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_connection()
        cursor = conn.cursor()

        # ❌ Controllo username già esistente
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Username già esistente")

        # ❌ Controllo email già registrata
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Email già registrata")

        # ✅ Inserimento nuovo utente con password hashata
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email, newsletter_optin)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, hashed_password, name, surname, phone, email, newsletter))

        conn.commit()
        conn.close()

        # ✅ Invio email di conferma registrazione
        invia_email_registrazione(email, name, surname, username, phone, password)

        return redirect(url_for('login_user'))

    return render_template('register.html')




@app.route('/admin_marketing', methods=['GET', 'POST'])
def admin_marketing():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = get_connection()
    cursor = conn.cursor()
    users = []
    min_days = None
    max_days = None

    if request.method == 'POST':
        min_days = int(request.form.get('min_days', 0))
        max_days = request.form.get('max_days')
        max_days = int(max_days) if max_days else None

        subject = request.form.get('subject')
        message = request.form.get('message')
        manual_email = request.form.get('manual_email')

        if manual_email:
            selected_emails = [manual_email]
        else:
            selected_emails = request.form.getlist('selected_users')

        success = 0
        for email in selected_emails:
            try:
                invia_email_marketing(email, subject, message)
                success += 1
            except Exception as e:
                print(f"Errore invio a {email}: {e}")

        conn.close()
        return f"""
        <html><head><meta http-equiv="refresh" content="5;url={url_for('admin_dashboard')}"></head><body>
        <h2>✅ Email inviate a {success} utenti.</h2>
        <p>Verrai reindirizzato tra 5 secondi...</p>
        <a href="{url_for('admin_dashboard')}"><button>← Torna subito</button></a>
        </body></html>
        """

    elif request.method == 'GET':
        min_days = request.args.get('min_days')
        max_days = request.args.get('max_days')

        if min_days:
            min_days = int(min_days)
            max_days = int(max_days) if max_days else 9999

            cursor.execute("""
                SELECT u.name || ' ' || u.surname, u.email,
                       ROUND(EXTRACT(DAY FROM NOW() - a.last_date::date)) AS giorni_passati
                FROM users u
                JOIN (
                    SELECT user_id, MAX(date) AS last_date
                    FROM appointments
                    GROUP BY user_id
                ) a ON u.id = a.user_id
                WHERE u.newsletter_optin = 1
                AND EXTRACT(DAY FROM NOW() - a.last_date::date) >= %s
                AND EXTRACT(DAY FROM NOW() - a.last_date::date) < %s
            """, (min_days, max_days))
            users = cursor.fetchall()

    conn.close()
    return render_template('admin_marketing.html', users=users, min_days=min_days, max_days=max_days)


@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    cursor.execute("""
        SELECT id, service, date, time
        FROM appointments
        WHERE user_id = %s AND (date > %s OR (date = %s AND time >= %s))
        ORDER BY date ASC, time ASC
    """, (user_id, today, today, now_time))

    appointments = cursor.fetchall()
    conn.close()

    return render_template('user_dashboard.html', appointments=appointments)

@app.route('/user_history')
def user_history():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT service, date, time
        FROM appointments
        WHERE user_id = %s AND (date < %s OR (date = %s AND time < %s))
        ORDER BY date DESC, time DESC
    """, (user_id, today, today, now_time))

    appointments = cursor.fetchall()
    conn.close()

    return render_template('user_history.html', appointments=appointments)


@app.route('/admin_hourly_calendar')
def admin_hourly_calendar():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))
    # prendo la data in query string, es. ?date=2025-04-26
    selected = request.args.get('date', '')
    return render_template('admin_calendar_hourly.html', selected_date=selected)



@app.route('/admin_add_user', methods=['GET', 'POST'])
def admin_add_user():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # ✅ Nuovo: gestione privacy obbligatoria
        privacy = request.form.get('privacy')
        if not privacy:
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, 0),
                                   error="Devi accettare la privacy")

        # ✅ Nuovo: newsletter facoltativa
        newsletter = 1 if request.form.get('newsletter') == 'on' else 0

        conn = get_connection()
        cursor = conn.cursor()

        # Verifica duplicati
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Username già esistente")

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Email già registrata")

        # Inserimento
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email, newsletter_optin)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, password, name, surname, phone, email, newsletter))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))

    # GET – form vuoto
    user = ("", "", "", "", "", "", 0)
    return render_template('admin_edit_user.html', user=user)



@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM appointments
        WHERE TO_DATE(date, 'YYYY-MM-DD') >= CURRENT_DATE
    """)
    total = cursor.fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    cursor.execute("""
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time, appointments.barber
        FROM appointments
        JOIN users ON appointments.user_id = users.id
        WHERE TO_DATE(appointments.date, 'YYYY-MM-DD') >= CURRENT_DATE
        ORDER BY TO_DATE(appointments.date, 'YYYY-MM-DD') ASC, appointments.time ASC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        appointments=appointments,
        page=page,
        total_pages=total_pages
    )




@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    if request.method == 'POST':
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        user_id = session['user_id']

        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            time_obj = datetime.strptime(time, "%H:%M").time()
            now = datetime.now()

            if date_obj.date() < now.date():
                return render_template('book.html', error="Non puoi prenotare in una data passata.")
            if date_obj.date() == now.date():
                appointment_datetime = datetime.combine(date_obj.date(), time_obj)
                if appointment_datetime < now + timedelta(hours=1):
                    return render_template('book.html', error="Devi prenotare almeno un'ora prima.")
            if date_obj.weekday() < 1 or date_obj.weekday() > 5:
                return render_template('book.html', error="Prenotabile solo da martedì a sabato.")
            if date_obj.weekday() == 5 and time > '15:30':
             return render_template('book.html', error="Sabato solo fino alle 15:30.")

        except:
            return render_template('book.html', error="Data o orario non validi.")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT barber FROM appointments
            WHERE date = %s AND time = %s
        """, (date, time))
        booked_barbers = [row[0] for row in cursor.fetchall()]

        assigned_barber = None
        for b in ['Achille', 'Mattia']:
            if b not in booked_barbers:
                assigned_barber = b
                break

        if not assigned_barber:
            conn.close()
            return render_template('book.html', error="Orario già pieno.")

        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, service, date, time, assigned_barber))

        conn.commit()

        # 📧 Invia email
        try:
            cursor.execute("SELECT name, email, phone FROM users WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()
            if user_info and user_info[1]:
                invia_email_appuntamento(
                    destinatario=user_info[1],
                    nome=user_info[0],
                    telefono=user_info[2],
                    email=user_info[1],
                    servizio=service,
                    data=date,
                    ora=time,
                    barbiere=assigned_barber
                )
        except Exception as e:
            print("❌ Errore nell'invio email appuntamento:", e)

        conn.close()
        return redirect(url_for('user_dashboard'))

    return render_template('book.html')


def invia_email_appuntamento(destinatario, nome, telefono, email, servizio, data, ora, barbiere=None):
    mittente = 'rubinimc@gmail.com'
    password = 'mtgk jhxz wagn wicg'  # Cambia con una password sicura

    # ---- Email al cliente ----
    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = "Conferma appuntamento – Les Klips Hair & Barber"

    corpo = f"""
Ciao {nome},

la tua prenotazione è stata confermata ✅

✂️ Servizio: {servizio}
📅 Data: {data}
⏰ Ora: {ora}

Ti aspettiamo da Les Klips Hair & Barber! 💈

Per modifiche o cancellazioni puoi farlo direttamente dal sito, oppure contattaci al numero: 051 683 0322 📞

— Lo staff di Les Klips
"""
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(mittente, password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("❌ Errore invio email cliente:", e)

    # ---- Copia al salone ----
    msg_salone = MIMEMultipart()
    msg_salone['From'] = mittente
    msg_salone['To'] = 'rubinimc@gmail.com'
    msg_salone['Subject'] = "📅 Nuova prenotazione ricevuta"

    corpo_salone = f"""
📬 Nuova prenotazione ricevuta!

👤 Cliente: {nome}
📞 Cellulare: {telefono}
📧 Email: {email}

✂️ Servizio: {servizio}
📅 Data: {data}
⏰ Ora: {ora}
💈 Barbiere: {barbiere or 'Non specificato'}

Controlla il gestionale per i dettagli.
"""
    msg_salone.attach(MIMEText(corpo_salone, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(mittente, password)
        server.send_message(msg_salone)
        server.quit()
    except Exception as e:
        print("❌ Errore invio email salone:", e)


@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if 'user_id' not in session and 'admin' not in session:
        return redirect(url_for('login_user'))

    conn = get_connection()
    cursor = conn.cursor()

    # 🔍 Carica appuntamento (incluso 'tipo')
    if 'admin' in session:
        cursor.execute("SELECT id, service, date, time, barber, tipo FROM appointments WHERE id = %s", (appointment_id,))
    else:
        cursor.execute("SELECT id, service, date, time, barber, tipo FROM appointments WHERE id = %s AND user_id = %s",
                       (appointment_id, session['user_id']))

    appointment = cursor.fetchone()
    if not appointment:
        conn.close()
        return redirect(url_for('admin_dashboard' if 'admin' in session else 'user_dashboard'))

    tipo = appointment[5]

    # ⛔️ Blocco modifica troppo vicina per l'utente
    if 'user_id' in session:
        appointment_datetime = datetime.strptime(f"{appointment[2]} {appointment[3]}", "%Y-%m-%d %H:%M")
        if datetime.now() > appointment_datetime - timedelta(hours=1):
            conn.close()
            template = 'edit_appointment_hair.html' if tipo == 'parrucchiera' else 'edit_appointment.html'
            return render_template(template, appointment=appointment,
                                   error="Non puoi modificare l'appuntamento meno di un'ora prima.")

    if request.method == 'POST':
        new_service = request.form['service']
        new_date = request.form['date']
        new_time = request.form['time']

        # ⛔️ Controllo se lo slot è pieno
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = %s AND time = %s AND id != %s",
                       (new_date, new_time, appointment_id))
        if cursor.fetchone()[0] >= 2:
            conn.close()
            template = 'edit_appointment_hair.html' if tipo == 'parrucchiera' else 'edit_appointment.html'
            return render_template(template, appointment=appointment,
                                   error="Fascia oraria piena.")

        # 🛠️ Se admin, aggiorna anche il barbiere
        if 'admin' in session:
            new_barber = request.form['barber']
            cursor.execute("""
                UPDATE appointments 
                SET service = %s, date = %s, time = %s, barber = %s 
                WHERE id = %s
            """, (new_service, new_date, new_time, new_barber, appointment_id))
        else:
            cursor.execute("""
                UPDATE appointments 
                SET service = %s, date = %s, time = %s 
                WHERE id = %s
            """, (new_service, new_date, new_time, appointment_id))

        conn.commit()
        conn.close()

        # 🔁 Redirect
        return redirect(url_for('admin_dashboard' if 'admin' in session else 'user_dashboard'))

    conn.close()
    template = 'edit_appointment_hair.html' if tipo == 'parrucchiera' and 'admin' in session else 'edit_appointment.html'
    return render_template(template, appointment=appointment)


@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, date, time FROM appointments WHERE id = %s", (appointment_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({'error': 'Appuntamento non trovato'}), 404

    user_id, date_str, time_str = result
    appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    now = datetime.now()

    # SE ADMIN: bypassa tutti i controlli
    if 'admin' in session:
        cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
        conn.commit()
        conn.close()
        return '', 204

    # SE UTENTE LOGGATO: controlli di sicurezza
    if 'user_id' in session:
        if session['user_id'] != user_id:
            conn.close()
            return jsonify({'error': 'Non sei autorizzato'}), 403
        if now > appointment_datetime:
            conn.close()
            return jsonify({'error': 'Appuntamento già passato'}), 403
        if now > appointment_datetime - timedelta(hours=1):
            conn.close()
            return jsonify({'error': 'Meno di un\'ora all\'appuntamento'}), 403

        cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
        conn.commit()
        conn.close()
        return '', 204

    conn.close()
    return jsonify({'error': 'Non autorizzato'}), 403

@app.route('/delete_all_appointments', methods=['POST'])
def delete_all_appointments():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/get_booked_times', methods=['POST'])
def get_booked_times():
    from collections import defaultdict
    data = request.get_json()
    date = data.get('date')
    tipo = data.get('tipo', 'parrucchiera')
    now = datetime.now()
    is_today = (date == now.strftime("%Y-%m-%d"))
    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()

    all_slots = [
        '09:00','09:30','10:00','10:30','11:00','11:30',
        '12:00','12:30','13:00','13:30','14:00','14:30',
        '15:00','15:30','16:00','16:30','17:00','17:30',
        '18:00','18:30','19:00'
    ]

    if weekday == 5:  # sabato
        all_slots = [t for t in all_slots if t <= '15:30']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time, user_id FROM appointments
        WHERE date = %s AND tipo = %s
    """, (date, tipo))
    results = cursor.fetchall()
    conn.close()

    slot_counts = defaultdict(lambda: {'clienti': 0, 'totali': 0})

    for time, user_id in results:
        if time in all_slots:
            slot_counts[time]['totali'] += 1
            if user_id and user_id > 0:
                slot_counts[time]['clienti'] += 1

    # Orari speciali dove il cliente può prenotare entrambi gli slot
    special_slots = []
    if weekday in [1, 2, 3, 4]:  # martedì-venerdì
        special_slots = ['09:00', '18:30']
    elif weekday == 5:  # sabato
        special_slots = ['09:00', '15:00']

    booked_times = []
    for t in all_slots:
        clienti = slot_counts[t]['clienti']
        if t in special_slots:
            if clienti >= 2:
                booked_times.append(t)
        else:
            if clienti >= 1:
                booked_times.append(t)

    too_close = []
    if is_today:
        for t in all_slots:
            slot_dt = datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
            if slot_dt < now + timedelta(hours=1):
                too_close.append(t)

    return jsonify({
        'booked_times': sorted(booked_times),
        'not_available_today': too_close
    })





@app.route('/admin_get_day_slots', methods=['POST'])
def admin_get_day_slots():
    if 'admin' not in session:
        return jsonify({'error': 'Non autorizzato'}), 403

    data = request.get_json()
    date = data.get('date')
    if not date:
        return jsonify({'error': 'Data mancante'}), 400
    
    # 🔒 Blocca lunedì e domenica
    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
    if weekday == 0 or weekday == 6:
        return jsonify({'slots': {}})  # Nessuno slot disponibile

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT users.name, users.phone, appointments.service, appointments.time, appointments.id, appointments.barber
    FROM appointments
    JOIN users ON users.id = appointments.user_id
    WHERE appointments.date = %s AND appointments.tipo = 'barbiere'
    """, (date,))

    records = cursor.fetchall()
    conn.close()

    all_times = [
        '09:00','09:30','10:00','10:30','11:00','11:30',
        '12:00','12:30','13:00','13:30','14:00','14:30',
        '15:00','15:30','16:00','16:30','17:00','17:30',
        '18:00','18:30','19:00'
    ]

    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()

    # Sabato: solo fino alle 15:00
    if weekday == 5:
        times = [t for t in all_times if t <= '15:30']
    else:
        times = all_times

    slots = {t: [] for t in times}
    for name, phone, servizio, time, app_id, barber in records:
        if time in slots:
            slots[time].append({
                'name': name,
                'phone': phone,
                'servizio': servizio,
                'id': app_id,
                'barber': barber
            })

    return jsonify({'slots': slots})

@app.route('/admin_get_day_slots_hair', methods=['POST'])
def admin_get_day_slots_hair():
    if 'admin' not in session:
        return jsonify({'error': 'Non autorizzato'}), 403

    data = request.get_json()
    date = data.get('date')
    if not date:
        return jsonify({'error': 'Data mancante'}), 400

    # Giorno della settimana (0=lunedì ... 6=domenica)
    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()

    # Genera tutti gli slot ogni mezz'ora dalle 09:00 alle 19:00
    all_slots = [f"{h:02d}:{m}" for h in range(9, 20) for m in ("00", "30")]

    # Se è sabato (weekday==5) limitiamo fino alle 15:30
    if weekday == 5:
        times = [t for t in all_slots if t <= "15:30"]
    else:
        times = all_slots

    # Inizializza dizionario degli slot
    slots = {t: [] for t in times}

    # Prendi tutte le prenotazioni 'parrucchiera' per quella data
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.name, u.phone, a.service, a.time, a.id, a.barber
        FROM appointments a
        JOIN users u ON u.id = a.user_id
        WHERE a.date = %s AND a.tipo = 'parrucchiera'
    """, (date,))
    records = cursor.fetchall()
    conn.close()

    # Popola lo slot corrispondente
    for name, phone, service, time_slot, app_id, barber in records:
        if time_slot in slots:
            slots[time_slot].append({
                'name': name,
                'phone': phone,
                'servizio': service,
                'id': app_id,
                'barber': barber
            })

    return jsonify({'slots': slots})


@app.route('/admin_book_hair', methods=['GET', 'POST'])
def admin_book_hair():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    date = request.args.get('date')
    time = request.args.get('time')

    if request.method == 'POST':
        name    = request.form['name'].strip()
        surname = request.form['surname'].strip()
        phone   = request.form['phone'].strip()
        service = request.form['service']
        date    = request.form['date']
        time    = request.form['time']
        barber  = request.form['barber']  # "Daniela"

        # Calcola durata in minuti
        duration_min = 90 if service == 'Taglio + Colore + Piega' else 60

        conn = get_connection()
        cursor = conn.cursor()

        # Cerca o crea utente
        cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
        u = cursor.fetchone()
        if u:
            user_id = u[0]
        else:
            # genera username univoco
            base = f"{name.lower()}.{surname.lower()}"[:20]
            uname = base
            suffix = 1
            cursor.execute("SELECT 1 FROM users WHERE username = %s", (uname,))
            while cursor.fetchone():
                uname = f"{base}{suffix}"
                suffix += 1
                cursor.execute("SELECT 1 FROM users WHERE username = %s", (uname,))
            
            # QUI usiamo RETURNING id
            cursor.execute("""
                INSERT INTO users (username, password, name, surname, phone)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (uname, 'admin-creato', name, surname, phone or 'ND'))
            user_id = cursor.fetchone()[0]

        # Controllo sovrapposizioni
        fmt = "%Y-%m-%d %H:%M"
        start_dt = datetime.strptime(f"{date} {time}", fmt)
        end_dt   = start_dt + timedelta(minutes=duration_min)

        cursor.execute("""
            SELECT service, time
            FROM appointments
            WHERE date = %s AND tipo = 'parrucchiera'
        """, (date,))
        for svc, t0 in cursor.fetchall():
            d0 = 90 if svc == 'Taglio + Colore + Piega' else 60
            s0 = datetime.strptime(f"{date} {t0}", fmt)
            e0 = s0 + timedelta(minutes=d0)
            if not (end_dt <= s0 or start_dt >= e0):
                conn.close()
                err = f"Intervallo {time}–{(start_dt+timedelta(minutes=duration_min)).strftime('%H:%M')} in conflitto con un altro appuntamento."
                return render_template('admin_book_hair.html', date=date, time=time, error=err)

        # Se è tutto libero, inserisci appuntamento
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber, tipo)
            VALUES (%s, %s, %s, %s, %s, 'parrucchiera')
        """, (user_id, service, date, time, barber))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_hourly_calendar'))

    # GET: mostra form
    return render_template('admin_book_hair.html', date=date, time=time)



@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        new_password = request.form['password']
        newsletter = 1 if request.form.get('newsletter') == 'on' else 0

        # ❌ Controlla username duplicato
        cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('account.html', error="Username già in uso.", user=None)

        # 🔐 Se la password è stata modificata, verifica e aggiorna
        if new_password:
            if not is_password_strong(new_password):
                conn.close()
                return render_template('account.html', error="La password deve contenere almeno 8 caratteri, una lettera, un numero e un simbolo.", user=None)

            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                UPDATE users 
                SET name = %s, surname = %s, phone = %s, email = %s, username = %s, password = %s, newsletter_optin = %s
                WHERE id = %s
            """, (name, surname, phone, email, username, hashed, newsletter, user_id))
        else:
            # Nessun cambio password
            cursor.execute("""
                UPDATE users 
                SET name = %s, surname = %s, phone = %s, email = %s, username = %s, newsletter_optin = %s
                WHERE id = %s
            """, (name, surname, phone, email, username, newsletter, user_id))

        conn.commit()
        conn.close()
        session['username'] = username
        return redirect(url_for('user_dashboard'))

    # GET: carica i dati utente senza mostrare la password
    cursor.execute("SELECT name, surname, phone, email, username, newsletter_optin FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template('account.html', user=user)


@app.route('/admin_history', methods=['GET', 'POST'])
def admin_history():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    filters = {
        'start_date': '',
        'end_date': '',
        'service': '',
        'search': ''
    }

    query = """
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time 
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE TO_DATE(appointments.date, 'YYYY-MM-DD') < CURRENT_DATE
    """
    params = []

    if request.method == 'POST':
        filters['start_date'] = request.form.get('start_date', '')
        filters['end_date'] = request.form.get('end_date', '')
        filters['service'] = request.form.get('service', '')
        filters['search'] = request.form.get('search', '')

        if filters['start_date']:
            query += " AND TO_DATE(appointments.date, 'YYYY-MM-DD') >= %s"
            params.append(filters['start_date'])

        if filters['end_date']:
            query += " AND TO_DATE(appointments.date, 'YYYY-MM-DD') <= %s"
            params.append(filters['end_date'])

        if filters['service']:
            query += " AND appointments.service = %s"
            params.append(filters['service'])

        if filters['search']:
            query += " AND (users.name ILIKE %s OR users.surname ILIKE %s OR users.phone ILIKE %s)"
            like = f"%{filters['search']}%"
            params.extend([like, like, like])

    query += " ORDER BY TO_DATE(appointments.date, 'YYYY-MM-DD') DESC, appointments.time DESC"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    appointments = cursor.fetchall()
    conn.close()

    return render_template('admin_history.html', appointments=appointments, filters=filters)



@app.route('/admin_stats', methods=['GET', 'POST'])
def admin_stats():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()

    # 🗓️ Anno e mese selezionati
    today = datetime.today()
    selected_year = today.year
    selected_month = today.month
    selected_tipo = 'tutti'

    if request.method == 'POST':
        selected_month = int(request.form.get('month', selected_month))
        selected_year = int(request.form.get('year', selected_year))
        selected_tipo = request.form.get('tipo', 'tutti')

    # 📆 Giorni del mese corrente filtrati
    cursor.execute("""
        SELECT TO_CHAR(DATE(date), 'YYYY-MM-DD') as giorno, COUNT(*) 
        FROM appointments 
        WHERE EXTRACT(MONTH FROM date::date) = %s
          AND EXTRACT(YEAR FROM date::date) = %s
          AND (%s = 'tutti' OR tipo = %s)
        GROUP BY giorno
        ORDER BY giorno
    """, (selected_month, selected_year, selected_tipo, selected_tipo))
    daily_data = cursor.fetchall()

    # 📊 Appuntamenti per mese dell’anno selezionato
    cursor.execute("""
        SELECT TO_CHAR(date::date, 'YYYY-MM') as mese, COUNT(*) 
        FROM appointments 
        WHERE EXTRACT(YEAR FROM date::date) = %s
          AND (%s = 'tutti' OR tipo = %s)
        GROUP BY mese
        ORDER BY mese
    """, (selected_year, selected_tipo, selected_tipo))
    monthly_data = cursor.fetchall()

    # 📅 Anni disponibili (per i filtri)
    cursor.execute("SELECT DISTINCT EXTRACT(YEAR FROM date::date)::int FROM appointments ORDER BY 1 DESC")
    available_years = [int(r[0]) for r in cursor.fetchall()]

    conn.close()

    return render_template(
        'admin_stats.html',
        daily_data=daily_data,
        monthly_data=monthly_data,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_tipo=selected_tipo,
        available_years=available_years
    )


@app.route('/admin_history/export', methods=['POST'])
def export_history_csv():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    query = """
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time, appointments.tipo
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE TO_DATE(appointments.date, 'YYYY-MM-DD') < CURRENT_DATE
    """
    params = []

    # Recupera filtri dal form
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    service = request.form.get('service', '')
    tipo = request.form.get('tipo', '')  # tipo = barbiere/parrucchiera
    search = request.form.get('search', '')

    if start_date:
        query += " AND TO_DATE(appointments.date, 'YYYY-MM-DD') >= %s"
        params.append(start_date)

    if end_date:
        query += " AND TO_DATE(appointments.date, 'YYYY-MM-DD') <= %s"
        params.append(end_date)

    if service:
        query += " AND appointments.service = %s"
        params.append(service)

    if tipo:
        query += " AND appointments.tipo = %s"
        params.append(tipo)

    if search:
        query += " AND (users.name ILIKE %s OR users.surname ILIKE %s OR users.phone ILIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])

    query += " ORDER BY TO_DATE(appointments.date, 'YYYY-MM-DD') DESC, appointments.time DESC"

    # Esegui query
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Genera CSV
    import csv
    from io import StringIO
    from flask import make_response

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Username', 'Nome', 'Cognome', 'Telefono', 'Servizio', 'Data', 'Ora', 'Tipo'])

    for row in rows:
        writer.writerow(row)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=storico_appuntamenti.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/book_hair', methods=['GET', 'POST'])
def book_hair():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    if request.method == 'POST':
        user_id = session['user_id']
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        barber = request.form['barber']  # Es. "Daniela"

        conn = get_connection()
        cursor = conn.cursor()

        # Controlla se lo slot è già prenotato dalla parrucchiera
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE date = %s AND time = %s AND barber = %s AND tipo = 'parrucchiera'
        """, (date, time, barber))
        if cursor.fetchone()[0] >= 1:
            conn.close()
            return render_template('book_hair.html', error="Orario già prenotato.")

        # Salva l'appuntamento
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber, tipo)
            VALUES (%s, %s, %s, %s, %s, 'parrucchiera')
        """, (user_id, service, date, time, barber))
        conn.commit()

        # 📧 Invio email di conferma
        try:
            cursor.execute("SELECT name, email, phone FROM users WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()
            if user_info and user_info[1]:
                invia_email_appuntamento(
                    destinatario=user_info[1],
                    nome=user_info[0],
                    telefono=user_info[2],
                    email=user_info[1],
                    servizio=service,
                    data=date,
                    ora=time,
                    barbiere=barber
                )
        except Exception as e:
            print("❌ Errore invio email appuntamento donna:", e)

        conn.close()
        return redirect(url_for('user_dashboard'))

    return render_template('book_hair.html')



@app.route('/admin_book', methods=['GET', 'POST'])
def admin_book():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    date = request.args.get('date')
    time = request.args.get('time')

    if request.method == 'POST':
        name    = request.form['name'].strip()
        surname = request.form['surname'].strip()
        phone   = request.form['phone'].strip()
        service = request.form['service']
        date    = request.form['date']
        time    = request.form['time']
        barber  = request.form['barber']

        conn = get_connection()
        cursor = conn.cursor()

        # 🔍 Cerca se esiste già l'utente con quel telefono
        cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
        existing_user = cursor.fetchone()

        if existing_user:
            user_id = existing_user[0]
        else:
            # ➡️ Se non esiste, crea un nuovo utente (admin-creato)
            base = f"{name.lower()}.{surname.lower()}"[:20]
            uname = base
            suffix = 1

            cursor.execute("SELECT 1 FROM users WHERE username = %s", (uname,))
            while cursor.fetchone():
                uname = f"{base}{suffix}"
                suffix += 1
                cursor.execute("SELECT 1 FROM users WHERE username = %s", (uname,))

            cursor.execute("""
                INSERT INTO users (username, password, name, surname, phone)
                VALUES (%s, %s, %s, %s, %s)
            """, (uname, 'admin-creato', name, surname, phone or 'ND'))

            conn.commit()

            cursor.execute("SELECT id FROM users WHERE username = %s", (uname,))
            user_id = cursor.fetchone()[0]

        # 📅 Ora abbiamo sicuramente un user_id valido

        # Controllo se slot è già pieno
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE date = %s AND time = %s
        """, (date, time))
        if cursor.fetchone()[0] >= 2:
            conn.close()
            return render_template('admin_book.html', date=date, time=time, error="Slot già pieno.")

        # Inserisci appuntamento con tipo barbiere
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber, tipo)
            VALUES (%s, %s, %s, %s, %s, 'barbiere')
        """, (user_id, service, date, time, barber))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    # GET: Form iniziale
    return render_template('admin_book.html', date=date, time=time)

if __name__ == '__main__':
    init_db()          # 👉 crea le tabelle se non esistono
    app.run(debug=True)


    #ciao csao mi racconti?

