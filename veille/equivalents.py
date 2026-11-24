import os
import re
from playwright.sync_api import sync_playwright

ZW = {ord(c): None for c in "\u200b\u200c\u200d\u2060\u2063\ufeff"}
RE_PRIX = re.compile(r"([\d\s\u202f\u00a0]+,\d{2})[\s\u202f\u00a0]*€")
RE_ID = re.compile(r"product\.php\?p=(\d+)")
JS = """() => Array.from(document.querySelectorAll('a[href*="product.php?p="]'))
        .map(a => ({href: a.getAttribute('href'), texte: a.innerText}))"""


def _nombre(t):
    return float(re.sub(r"[\s\u202f\u00a0]", "", t).replace(",", "."))


def _lire_page(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    produits = {}
    for it in page.evaluate(JS):
        m = RE_ID.search(it["href"] or "")
        if not m:
            continue
        texte = (it["texte"] or "").translate(ZW)
        lignes = [l.strip() for l in texte.split("\n") if l.strip()]
        if not lignes:
            continue
        prix = None
        for l in reversed(lignes):
            mp = RE_PRIX.search(l)
            if mp:
                prix = _nombre(mp.group(1))
                break
        pid = m.group(1)
        if pid not in produits or len(texte) > produits[pid]["len"]:
            produits[pid] = {"nom": lignes[0], "prix": prix, "len": len(texte)}
    return produits


def lire_recherches(recherches):
    """Renvoie {nom_recherche: {id_produit: {nom, prix}}}."""
    resultats = {}
    headless = os.environ.get("HEADLESS") == "1"
    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(channel="chrome", headless=headless)
        except Exception:
            nav = p.chromium.launch(headless=headless)
        page = nav.new_page()
        for r in recherches:
            try:
                res = _lire_page(page, r["url"])
                print(f"[equiv] {r['nom']} : {len(res)} produits lus")
                resultats[r["nom"]] = res
            except Exception as e:
                print(f"[equiv] {r['nom']} -> ERREUR {str(e)[:100]}")
        nav.close()
    return resultats
