import os
import re
from playwright.sync_api import sync_playwright

def _nombre(texte: str):
    t = texte.replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    m = re.search(r"\d+(?:[.,]\d+)?", t)
    return float(m.group().replace(",", ".")) if m else None

def _connexion(page):
    return _nombre(page.locator("div.fs-1.fontTitre").first.inner_text())

def _primo_ideo(page):
    return _nombre(page.locator("[itemprop=price]").first.get_attribute("content"))

EXTRACTEURS = {"connexion": _connexion, "primo-ideo": _primo_ideo}

def lire_prix_sources(sources):
    """sources: liste de {site, url}. Renvoie {url: prix ou None}."""
    resultats = {}
    headless = os.environ.get("HEADLESS") == "1"
    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(channel="chrome", headless=headless)
        except Exception:
            nav = p.chromium.launch(headless=headless)
        page = nav.new_page()
        for s in sources:
            try:
                rep = page.goto(s["url"], wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                prix = EXTRACTEURS[s["site"]](page)
                print(f"[prix] {s['site']} -> HTTP {rep.status if rep else '?'}, prix {prix}")
                resultats[s["url"]] = prix
            except Exception as e:
                print(f"[prix] {s['site']} -> ERREUR {str(e)[:100]}")
                resultats[s["url"]] = None
        nav.close()
    return resultats
