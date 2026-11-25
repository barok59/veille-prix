import re
import requests
import feedparser

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

FLUX = ["https://www.dealabs.com/rss/tous"]


def charger_deals():
    deals = []
    for url in FLUX:
        r = requests.get(url, headers=HEADERS, timeout=20)
        flux = feedparser.parse(r.content)
        print(f"[dealabs] {url} -> HTTP {r.status_code}, {len(flux.entries)} entrée(s)")
        for e in flux.entries:
            texte = e.title + " " + e.get("summary", "")
            deals.append({"titre": e.title, "lien": e.link, "texte": texte})
    return deals


def normaliser(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def filtrer(deals, mots_cles, exclure=None, champ="texte"):
    """champ : 'titre' ou 'texte' (titre + description)."""
    cles = [normaliser(m) for m in mots_cles]
    excl = [normaliser(m) for m in (exclure or [])]
    resultat = []
    for d in deals:
        t = normaliser(d[champ])
        if any(c in t for c in cles) and not any(x in t for x in excl):
            resultat.append(d)
    return resultat
