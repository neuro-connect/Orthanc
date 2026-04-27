import os
import requests
from aiosmtpd.controller import Controller
from email.parser import BytesParser
from email.policy import default

# Configuration via variables d'environnement
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@votre-domaine.com")
SENDER_NAME = os.getenv("SENDER_NAME", "Keycloak Auth")

class BrevoRelayHandler:
    async def handle_DATA(self, server, session, envelope):
        # Extraction du contenu du mail
        msg = BytesParser(policy=default).parsebytes(envelope.content)
        subject = msg['subject']
        body = msg.get_body(preferencelist=('html', 'plain')).get_content()
        recipient = envelope.rcpt_tos[0]

        print(f"Envoi d'un mail à {recipient} via Brevo API...")

        # Appel API Brevo
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
        payload = {
            "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
            "to": [{"email": recipient}],
            "subject": subject,
            "htmlContent": body
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 201:
            print("Succès !")
            return '250 Message accepted for delivery'
        else:
            print(f"Erreur Brevo: {response.text}")
            return '451 Requested action aborted: local error in processing'

if __name__ == '__main__':
    handler = BrevoRelayHandler()
    controller = Controller(handler, hostname='0.0.0.0', port=2525)
    print("Le relais SMTP-vers-Brevo écoute sur le port 2525...")
    controller.start()
    try:
        import asyncio
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        controller.stop()
