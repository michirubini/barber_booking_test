import psycopg2
import random
from datetime import datetime, timedelta

# Connessione al database PostgreSQL
conn = psycopg2.connect(
    dbname="barber_booking",
    user="postgres",
    password="admin",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Servizi e orari possibili
servizi_barbiere = ["Taglio di capelli", "Solo Barba", "Taglio di capelli + Barba"]
servizi_parrucchiera = ["Piega", "Colore", "Taglio donna", "Meches", "Balayage"]
orari = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30"
]
barbieri = ["Mattia", "Achille"]
parrucchiere = ["Francesca", "Giulia"]

# Prendi gli utenti con newsletter attiva
cursor.execute("SELECT id, name, surname FROM users WHERE newsletter_optin = 1")
utenti = cursor.fetchall()

count = 0
for user_id, name, surname in utenti:
    num_appuntamenti = random.randint(1, 3)
    for _ in range(num_appuntamenti):
        # 50% possibilità che sia nel futuro, 50% nel passato
        if random.random() < 0.5:
            giorni_offset = random.randint(1, 30)
            data_app = (datetime.now() + timedelta(days=giorni_offset)).strftime('%Y-%m-%d')
        else:
            giorni_offset = random.randint(5, 60)
            data_app = (datetime.now() - timedelta(days=giorni_offset)).strftime('%Y-%m-%d')

        ora_app = random.choice(orari)

        # Scegli casualmente se barbiere o parrucchiera
        tipo = random.choice(["barbiere", "parrucchiera"])
        if tipo == "barbiere":
            servizio = random.choice(servizi_barbiere)
            operatore = random.choice(barbieri)
        else:
            servizio = random.choice(servizi_parrucchiera)
            operatore = random.choice(parrucchiere)

        try:
            cursor.execute("""
                INSERT INTO appointments (user_id, date, time, service, barber, tipo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, data_app, ora_app, servizio, operatore, tipo))
            print(f"✔️ {tipo.upper()} – {name} {surname} → {data_app} {ora_app} – {servizio}")
            count += 1
        except Exception as e:
            print(f"⚠️ Errore: {e}")

conn.commit()
conn.close()
print(f"\n✅ Appuntamenti finti aggiunti: {count}")


