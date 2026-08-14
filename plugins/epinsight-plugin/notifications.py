import urllib.request
import urllib.error
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

current_dir = os.path.dirname(os.path.abspath(__file__))
env = Environment(
    loader=FileSystemLoader(os.path.join(current_dir, "templates")), autoescape=select_autoescape()
)

class Notification:
    def __init__(self, recipient, subject):
        self.recipient = recipient
        self.sender = os.getenv("BREVO_EMAIL")
        self.api_key = os.getenv("BREVO_API_KEY")
        self.name = os.getenv("BREVO_NAME")
        self.subject = subject
        self.template = None
        self.body = None

    def render_template(self, **kwargs):
        self.body = self.template.render(**kwargs)

    def send(self):
        url = "https://api.brevo.com/v3/smtp/email"
    
        # Prepare the payload
        payload = {
            "sender": {"name": "ONSET-PACS", "email": self.sender},
            "to": [{"email": self.recipient}],
            "subject": self.subject,
            "htmlContent": self.body
        }
        
        # Convert dictionary to JSON bytes
        data = json.dumps(payload).encode('utf-8')
        
        # Configure the request
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header("accept", "application/json")
        req.add_header("api-key", self.api_key)
        req.add_header("content-type", "application/json")

        try:
            # Execute the request
            with urllib.request.urlopen(req) as response:
                status = response.getcode()
                response_body = response.read().decode('utf-8')
                
                if status == 201:
                    print(f"Success! Email sent to {self.recipient}.")
                else:
                    print(f"Unexpected response ({status}): {response_body}")
                    
        except urllib.error.HTTPError as e:
            # Handle API errors (400, 401, etc.)
            error_info = e.read().decode('utf-8')
            print(f"HTTP Error {e.code}: {error_info}")
        except urllib.error.URLError as e:
            # Handle connection/DNS errors
            print(f"Connection Error: {e.reason}")


class JobNotification(Notification):
    def __init__(self, recipient, subject):
        super().__init__(recipient, subject)
        self.template = env.get_template("email/email_job_notification.html")
