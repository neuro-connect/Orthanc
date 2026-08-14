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
        try:
            msg = BytesParser(policy=default).parsebytes(envelope.content)
            subject = msg['subject'] or "(sans objet)"

            # --- Extraction robuste du corps ---
            part = msg.get_body(preferencelist=('html', 'plain'))
            if part is None:
                # Message sans corps structuré : on prend le brut si possible
                if not msg.is_multipart():
                    raw = msg.get_content()
                    html_content = f"<pre>{raw}</pre>"
                else:
                    html_content = "<pre>(message sans corps)</pre>"
            elif part.get_content_type() == 'text/plain':
                # Brevo exige du HTML : on enrobe le texte brut
                html_content = f"<pre>{part.get_content()}</pre>"
            else:
                html_content = part.get_content()

            # Filet de sécurité : ne jamais envoyer un htmlContent vide
            if not html_content or not html_content.strip():
                html_content = "<pre>(contenu vide)</pre>"

            recipient = envelope.rcpt_tos[0]
            print(f"Envoi d'un mail à {recipient} via Brevo API...", flush=True)

            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
            }
            payload = {
                "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": html_content,
            }

            response = requests.post(url, json=payload, headers=headers, timeout=15)

            if response.status_code == 201:
                print("Succès !", flush=True)
                return '250 Message accepted for delivery'
            else:
                print(f"Erreur Brevo ({response.status_code}): {response.text}", flush=True)
                return '451 Requested action aborted: local error in processing'

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Exception dans handle_DATA: {e}", flush=True)
            return '451 Requested action aborted: local error in processing'


if __name__ == '__main__':
    handler = BrevoRelayHandler()
    controller = Controller(handler, hostname='0.0.0.0', port=2525)
    print("Le relais SMTP-vers-Brevo écoute sur le port 2525...", flush=True)
    controller.start()
    try:
        import asyncio
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        controller.stop()