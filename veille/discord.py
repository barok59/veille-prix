import os
import requests

def envoyer(contenu: str):
    url = os.environ["DISCORD_WEBHOOK_URL"]
    r = requests.post(url, json={"content": contenu[:2000]}, timeout=15)
    r.raise_for_status()
