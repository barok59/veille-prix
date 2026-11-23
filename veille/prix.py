import os
import re
from playwright.sync_api import sync_playwright

ESP = r"[\s\u202f\u00a0]"
RE_DES = re.compile(rf"d[èe]s{ESP}+([\d\s\u202f\u00a0]+(?:[,.]\d{{1,2}})?){ESP}*€", re.IGNORECASE)
RE_OFFRE = re.compile(rf"^(.+?), .+, ([\d\s\u202f\u00a0]+,\d{{2}}){ESP}*€$")


def _nombre(texte: str):
    t = texte.replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    m = re.search(r"\d+(?:[.,]\d+)?", t)
    return float(m.group().replace(",", ".")) if m else None


def _connexion(page):
    return _nombre(page.locator("div.fs-1.fontTitre").first.inner_text()), None


def _primo_ideo(page):
    return _nombre(page.locator("[itemprop=price]").first.get_attribute("content")), None


def _ledenicheur(page):
    try:
        meta = page.locator('meta[name="description"]').first.get_attribute("content", timeout=3000) or ""
    except Exception:
        meta = ""
    titre = page.title()
    corps = page.inner_text("body")

    # On ne regarde que la zone des offres (évite les « Produits populaires »)
    debut = corps.find("Comparer les prix")
    fin = corps.find("Nous avons trouvé ce produit")
    if debut != -1 and fin > debut:
        section = corps[debut:fin]
    elif debut != -1:
        section = corps[debut:debut + 1500]
    else:
        section = ""

    prix = None
    for source in (titre, meta, section):
        m = RE_DES.search(source)
        if m:
            prix = _nombre(m.group(1))
            break

    meilleur, vendeur = None, None
    for ligne in section.split("\n"):
        mo = RE_OFFRE.match(ligne.strip())
        if mo:
            v = _nombre(mo.group(2))
            if v is not None and (meilleur is None or v < meilleur):
                meilleur, vendeur = v, mo.group(1)
    if prix is None:
        prix = meilleur
    if prix is not None and meilleur is not None and abs(meilleur - prix) > 0.01:
        vendeur = None  # incohérence : on n'affiche pas de vendeur

    if prix is None:
        print(f"[debug] titre={titre[:80]!r}")
        print(f"[debug] meta={meta[:80]!r}")
        print(f"[debug] section={' | '.join(section.split())[:300]!r}")
    return prix, vendeur


EXTRACTEURS = {"connexion": _connexion, "primo-ideo": _primo_ideo,
               "ledenicheur": _ledenicheur}


def lire_prix_sources(sources):
    """Renvoie {url: (prix, vendeur)}."""
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
                page.wait_for_timeout(3000)
                prix, vendeur = EXTRACTEURS[s["site"]](page)
                print(f"[prix] {s['site']} -> HTTP {rep.status if rep else '?'}, "
                      f"prix {prix}, vendeur {vendeur}")
                resultats[s["url"]] = (prix, vendeur)
            except Exception as e:
                print(f"[prix] {s['site']} -> ERREUR {str(e)[:100]}")
                resultats[s["url"]] = (None, None)
        nav.close()
    return resultats
