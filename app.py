from flask import Flask, render_template, request, redirect, url_for, session, jsonify # type: ignore
import sqlite3
from datetime import datetime, timedelta
import bcrypt
import uuid
import re




app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ---------- INIZIALIZZAZIONE DB ----------
def init_db():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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
        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            user_id = user[0]
            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(minutes=30)

            cursor.execute("""
                INSERT INTO password_tokens (user_id, token, expires_at)
                VALUES (?, ?, ?)
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

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    return '', 204


@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and bcrypt.checkpw(password.encode('utf-8'), admin[2].encode('utf-8')):  # admin[2] = password hash
            session['admin'] = admin[0]
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Credenziali non valide"

    return render_template('login_admin.html', error=error)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token')
    error = None
    success = None
    show_form = True

    if not token:
        return "Token mancante", 400

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Verifica token esistente
    cursor.execute("""
        SELECT pt.user_id, pt.expires_at, pt.used
        FROM password_tokens pt
        WHERE pt.token = ?
    """, (token,))
    token_data = cursor.fetchone()

    if not token_data:
        conn.close()
        return render_template("reset_password.html", error="Token non valido.", show_form=False)

    user_id, expires_at_str, used = token_data

    # ✅ Fix conversione con millisecondi
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
    except ValueError:
        conn.close()
        return render_template("reset_password.html", error="Errore nella validità del token.", show_form=False)

    if used:
        conn.close()
        return render_template("reset_password.html", error="Questo link è già stato utilizzato.", show_form=False)

    if datetime.now() > expires_at:
        conn.close()
        return render_template("reset_password.html", error="Il link per reimpostare la password è scaduto.", show_form=False)

    # POST → aggiorna la password
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            return render_template("reset_password.html", error="Le password non coincidono.", show_form=True)

        # Cripta la nuova password
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Aggiorna nel DB e segna il token come usato
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
        cursor.execute("UPDATE password_tokens SET used = 1 WHERE token = ?", (token,))
        conn.commit()
        conn.close()

        success = "✅ La tua password è stata reimpostata con successo!"
        return render_template("reset_password.html", success=success, show_form=False)

    conn.close()
    return render_template("reset_password.html", show_form=True)


@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
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

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    if search_query:
        search = f"%{search_query}%"
        cursor.execute("""
            SELECT COUNT(*) FROM users
            WHERE name LIKE ? OR surname LIKE ? OR phone LIKE ? OR email LIKE ?
        """, (search, search, search, search))
        total_users = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, name, surname, phone, email, username
            FROM users
            WHERE name LIKE ? OR surname LIKE ? OR phone LIKE ? OR email LIKE ?
            ORDER BY id
            LIMIT ? OFFSET ?
        """, (search, search, search, search, per_page, offset))
    else:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, name, surname, phone, email, username
            FROM users
            ORDER BY id
            LIMIT ? OFFSET ?
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
        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # Prima cancella gli appuntamenti legati
        cursor.executemany("DELETE FROM appointments WHERE user_id = ?", [(uid,) for uid in selected_ids])
        # Poi elimina gli utenti
        cursor.executemany("DELETE FROM users WHERE id = ?", [(uid,) for uid in selected_ids])

        conn.commit()
        conn.close()

    return redirect(url_for('admin_users'))

@app.route('/admin_edit_user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
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
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Username già in uso")

        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Email già registrata")

        # Salva modifiche
        cursor.execute("""
            UPDATE users 
            SET name = ?, surname = ?, phone = ?, email = ?, username = ?, password = ?, newsletter_optin = ?
            WHERE id = ?
        """, (name, surname, phone, email, username, password, newsletter, user_id))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))

    # Carica dati utente (incluso newsletter_optin)
    cursor.execute("SELECT name, surname, phone, email, username, password, newsletter_optin FROM users WHERE id = ?", (user_id,))
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

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    return render_template('goodbye.html')




@app.route('/admin_delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM appointments WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

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

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # ❌ Controllo username già esistente
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Username già esistente")

        # ❌ Controllo email già registrata
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Email già registrata")

        # ✅ Inserimento nuovo utente con password hashata
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email, newsletter_optin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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

    conn = sqlite3.connect('bookings.db')
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
                       ROUND(julianday('now') - julianday(a.last_date)) as giorni_passati
                FROM users u
                JOIN (
                    SELECT user_id, MAX(date) as last_date
                    FROM appointments
                    GROUP BY user_id
                ) a ON u.id = a.user_id
                WHERE u.newsletter_optin = 1
                AND julianday('now') - julianday(a.last_date) >= ?
                AND julianday('now') - julianday(a.last_date) < ?
            """, (min_days, max_days))
            users = cursor.fetchall()

    conn.close()
    return render_template('admin_marketing.html', users=users, min_days=min_days, max_days=max_days)


@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    cursor.execute("""
        SELECT id, service, date, time
        FROM appointments
        WHERE user_id = ? AND (date > ? OR (date = ? AND time >= ?))
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

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT service, date, time
        FROM appointments
        WHERE user_id = ? AND (date < ? OR (date = ? AND time < ?))
        ORDER BY date DESC, time DESC
    """, (user_id, today, today, now_time))

    appointments = cursor.fetchall()
    conn.close()

    return render_template('user_history.html', appointments=appointments)
@app.route('/admin_hourly_calendar')
def admin_hourly_calendar():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))
    return render_template('admin_calendar_hourly.html')


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

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # Verifica duplicati
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Username già esistente")

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password, newsletter),
                                   error="Email già registrata")

        # Inserimento
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email, newsletter_optin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.commit()
    cursor.execute("""
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time, appointments.barber
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE appointments.date >= ?
        ORDER BY DATE(appointments.date), TIME(appointments.time)
    """, (today,))
    appointments = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', appointments=appointments)

from flask import request, session, redirect, url_for, render_template # type: ignore
from datetime import datetime, timedelta
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT barber FROM appointments
            WHERE date = ? AND time = ?
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
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, service, date, time, assigned_barber))

        conn.commit()

        # 📧 Invia email
        try:
            cursor.execute("SELECT name, email, phone FROM users WHERE id = ?", (user_id,))
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

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # 🔍 Carica appuntamento (incluso 'tipo')
    if 'admin' in session:
        cursor.execute("SELECT id, service, date, time, barber, tipo FROM appointments WHERE id = ?", (appointment_id,))
    else:
        cursor.execute("SELECT id, service, date, time, barber, tipo FROM appointments WHERE id = ? AND user_id = ?",
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
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ? AND time = ? AND id != ?",
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
                SET service = ?, date = ?, time = ?, barber = ? 
                WHERE id = ?
            """, (new_service, new_date, new_time, new_barber, appointment_id))
        else:
            cursor.execute("""
                UPDATE appointments 
                SET service = ?, date = ?, time = ? 
                WHERE id = ?
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
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, date, time FROM appointments WHERE id = ?", (appointment_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({'error': 'Appuntamento non trovato'}), 404

    user_id, date_str, time_str = result
    appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    now = datetime.now()

    # SE ADMIN: bypassa tutti i controlli
    if 'admin' in session:
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
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

        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        conn.commit()
        conn.close()
        return '', 204

    conn.close()
    return jsonify({'error': 'Non autorizzato'}), 403

@app.route('/delete_all_appointments', methods=['POST'])
def delete_all_appointments():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/get_booked_times', methods=['POST'])
def get_booked_times():
    data = request.get_json()
    date = data.get('date')
    tipo = data.get('tipo', 'barbiere')  # "barbiere" o "parrucchiera"

    from datetime import datetime, timedelta
    now = datetime.now()
    is_today = date == now.strftime("%Y-%m-%d")

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # 📊 Conta le prenotazioni per ogni orario (solo per barbiere)
    cursor.execute("""
        SELECT time, COUNT(*) 
        FROM appointments 
        WHERE date = ? AND tipo = ? 
        GROUP BY time
    """, (date, tipo))
    results = cursor.fetchall()
    conn.close()

    # 👤 Il cliente può prenotare solo se ci sono meno di 1 prenotazione
    prenotazioni_per_orario = {row[0]: row[1] for row in results}
    booked_times = [time for time, count in prenotazioni_per_orario.items() if count >= 1]

    # ⏳ Blocca orari troppo vicini (meno di 1 ora da adesso)
    all_slots = [
        '09:00','09:30','10:00','10:30','11:00','11:30',
        '12:00','12:30','13:00','13:30','14:00','14:30',
        '15:00','15:30','16:00','16:30','17:00','17:30',
        '18:00','18:30','19:00'
    ]

    too_close = []
    if is_today:
        for t in all_slots:
            slot_time = datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
            if slot_time < now + timedelta(hours=1):
                too_close.append(t)

    return jsonify({
        'booked_times': booked_times,
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

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("""
    SELECT users.name, users.phone, appointments.service, appointments.time, appointments.id, appointments.barber
    FROM appointments
    JOIN users ON users.id = appointments.user_id
    WHERE appointments.date = ? AND appointments.tipo = 'barbiere'
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
    
    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
    if weekday == 0 or weekday == 6:
        return jsonify({'slots': {}})

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("""
    SELECT users.name, users.phone, appointments.service, appointments.time, appointments.id, appointments.barber
    FROM appointments
    JOIN users ON users.id = appointments.user_id
    WHERE appointments.date = ? AND appointments.tipo = 'parrucchiera'
""", (date,))

    records = cursor.fetchall()
    conn.close()

    all_times = ['09:00','10:00','11:00','12:00','13:00','14:00',
                 '15:00','16:00','17:00','18:00','19:00']

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


@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # ✅ Newsletter opzionale
        newsletter = 1 if request.form.get('newsletter') == 'on' else 0

        # ❌ Username duplicato?
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('account.html', error="Username già in uso.", user=None)

        # ✅ Aggiorna i dati
        cursor.execute("""
            UPDATE users 
            SET name = ?, surname = ?, phone = ?, email = ?, username = ?, password = ?, newsletter_optin = ?
            WHERE id = ?
        """, (name, surname, phone, email, username, password, newsletter, user_id))
        
        conn.commit()
        conn.close()

        # 🔁 Aggiorna anche la sessione
        session['username'] = username

        return redirect(url_for('user_dashboard'))

    # GET – Carica i dati utente (incluso newsletter_optin)
    cursor.execute("SELECT name, surname, phone, email, username, password, newsletter_optin FROM users WHERE id = ?", (user_id,))
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
        WHERE appointments.date < date('now')
    """
    params = []

    if request.method == 'POST':
        filters['start_date'] = request.form.get('start_date', '')
        filters['end_date'] = request.form.get('end_date', '')
        filters['service'] = request.form.get('service', '')
        filters['search'] = request.form.get('search', '')

        if filters['start_date']:
            query += " AND appointments.date >= ?"
            params.append(filters['start_date'])

        if filters['end_date']:
            query += " AND appointments.date <= ?"
            params.append(filters['end_date'])

        if filters['service']:
            query += " AND appointments.service = ?"
            params.append(filters['service'])

        if filters['search']:
            query += " AND (users.name LIKE ? OR users.surname LIKE ? OR users.phone LIKE ?)"
            like = f"%{filters['search']}%"
            params.extend([like, like, like])

    query += " ORDER BY DATE(appointments.date) DESC, TIME(appointments.time) DESC"

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    appointments = cursor.fetchall()
    conn.close()

    return render_template('admin_history.html', appointments=appointments, filters=filters)

@app.route('/admin_stats')
def admin_stats():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Appuntamenti per giorno
    cursor.execute("""
        SELECT date, COUNT(*) 
        FROM appointments 
        GROUP BY date 
        ORDER BY date
    """)
    daily_data = cursor.fetchall()

    # Appuntamenti per mese (yyyy-mm)
    cursor.execute("""
        SELECT SUBSTR(date, 1, 7) as month, COUNT(*)
        FROM appointments
        GROUP BY month
        ORDER BY month
    """)
    monthly_data = cursor.fetchall()

    conn.close()

    return render_template(
        'admin_stats.html',
        daily_data=daily_data,
        monthly_data=monthly_data
    )

@app.route('/admin_history/export', methods=['POST'])
def export_history_csv():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    query = """
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time 
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE appointments.date < date('now')
    """
    params = []

    # Recupera filtri dal form
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    service = request.form.get('service', '')
    search = request.form.get('search', '')

    if start_date:
        query += " AND appointments.date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND appointments.date <= ?"
        params.append(end_date)

    if service:
        query += " AND appointments.service = ?"
        params.append(service)

    if search:
        query += " AND (users.name LIKE ? OR users.surname LIKE ? OR users.phone LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    query += " ORDER BY DATE(appointments.date) DESC, TIME(appointments.time) DESC"

    # Esegui query
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Genera CSV
    import csv
    from io import StringIO
    from flask import make_response # type: ignore

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Username', 'Nome', 'Cognome', 'Telefono', 'Servizio', 'Data', 'Ora'])

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

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # Controlla se lo slot è già prenotato dalla parrucchiera
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE date = ? AND time = ? AND barber = ? AND tipo = 'parrucchiera'
        """, (date, time, barber))
        if cursor.fetchone()[0] >= 1:
            conn.close()
            return render_template('book_hair.html', error="Orario già prenotato.")

        # Salva l'appuntamento
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber, tipo)
            VALUES (?, ?, ?, ?, ?, 'parrucchiera')
        """, (user_id, service, date, time, barber))
        conn.commit()

        # 📧 Invio email di conferma
        try:
            cursor.execute("SELECT name, email, phone FROM users WHERE id = ?", (user_id,))
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
        name = request.form['name'].strip()
        surname = request.form['surname'].strip()
        phone = request.form['phone'].strip()
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        barber = request.form['barber']

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        user = None

        # 🔍 Se il numero è stato inserito, cerca l'utente
        if phone:
            cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            user = cursor.fetchone()

        # 👤 Se non esiste, crea nuovo utente con username univoco
        if not user:
            base_username = f"{name.lower()}.{surname.lower()}"[:20]
            username = base_username
            suffix = 1

            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            while cursor.fetchone():
                username = f"{base_username}{suffix}"
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                suffix += 1

            cursor.execute("""
                INSERT INTO users (username, password, name, surname, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (username, 'admin-creato', name, surname, phone if phone else "ND"))
            user_id = cursor.lastrowid
        else:
            user_id = user[0]

        # ⛔️ Controllo: massimo 2 appuntamenti nello stesso slot
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ? AND time = ?", (date, time))
        if cursor.fetchone()[0] >= 2:
            conn.close()
            return render_template("admin_book.html", date=date, time=time, error="Slot già pieno")

        # ✅ Inserimento appuntamento
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, service, date, time, barber))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_book.html", date=date, time=time)

if __name__ == '__main__':
    app.run(debug=True)

