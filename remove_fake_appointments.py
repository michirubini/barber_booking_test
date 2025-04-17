import sqlite3
from datetime import datetime

# Connessione al DB
conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

oggi = datetime.now().strftime('%Y-%m-%d')

# Cancella solo appuntamenti vecchi associati a utenti testabili
cursor.execute("""
    DELETE FROM appointments
    WHERE user_id IN (
        SELECT id FROM users WHERE newsletter_optin = 1
    )
    AND date < ?
""", (oggi,))

eliminati = cursor.rowcount
conn.commit()
conn.close()

print(f"\n🧽 Rimossi {eliminati} appuntamenti finti (con date passate).")
