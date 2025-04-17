import sqlite3
import random
from datetime import datetime, timedelta

# Connessione al database
conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

# Servizi e orari possibili
servizi = ["Taglio di capelli", "Solo Barba", "Taglio + Barba"]
orari = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
         "12:00", "12:30", "14:00", "14:30", "15:00", "15:30",
         "16:00", "16:30", "17:00", "17:30", "18:00", "18:30"]

# Trova utenti con newsletter attiva
cursor.execute("SELECT id, name, surname FROM users WHERE newsletter_optin = 1")
utenti = cursor.fetchall()

# Aggiungi appuntamenti finti
for user_id, name, surname in utenti:
    numero_appuntamenti = random.randint(1, 3)
    for _ in range(numero_appuntamenti):
        giorni_fa = random.randint(5, 60)
        data_app = (datetime.now() - timedelta(days=giorni_fa)).strftime('%Y-%m-%d')
        ora_app = random.choice(orari)
        servizio = random.choice(servizi)
        barbiere = "Mattia"

        cursor.execute("""
            INSERT INTO appointments (user_id, date, time, service, barber)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, data_app, ora_app, servizio, barbiere))

        print(f"Aggiunto: {name} {surname} → {data_app} {ora_app} – {servizio}")

# Salva e chiudi
conn.commit()
conn.close()

print("\n✅ Appuntamenti finti aggiunti con successo!")
