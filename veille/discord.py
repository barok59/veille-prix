import os
import requests


def envoyer(contenu: str):
    url = os.environ["DISCORD_WEBHOOK_URL"]
    r = requests.post(url, json={"content": contenu[:2000]}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Discord a répondu HTTP {r.status_code} (webhook invalide ou supprimé ?)")


def envoyer_long(contenu: str, limite: int = 1900):
    """Découpe en plusieurs messages sans couper une ligne."""
    blocs, courant = [], ""
    for ligne in contenu.split("\n"):
        ligne = ligne[:limite]
        if courant and len(courant) + len(ligne) + 1 > limite:
            blocs.append(courant)
            courant = ""
        courant += ligne + "\n"
    if courant.strip():
        blocs.append(courant)
    for b in blocs:
        envoyer(b.rstrip("\n"))
