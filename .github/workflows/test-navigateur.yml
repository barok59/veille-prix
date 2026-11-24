import re
from playwright.sync_api import sync_playwright

RECHERCHES = {
    "pyrolyse": "https://ledenicheur.fr/c/fours-encastres?1261=2377&559=120602&sort=price",
    "lave-vaisselle": "https://ledenicheur.fr/c/lave-vaisselle?105009=37012%7C37013%7C37010%7C37011&1261=2377&99385=32213&r_lowestPrice=381.8-1028.1&sort=price",
    "hotte": "https://ledenicheur.fr/c/hottes-aspirantes?108154=120577&1261=2380%7C28968%7C2379&4388=5811&r_lowestPrice=290.9-886.5&sort=price",
    "vapeur": "https://ledenicheur.fr/c/fours-encastres?1261=2377&559=120603&r_lowestPrice=306-1243.3&sort=price",
    "plaque": "https://ledenicheur.fr/c/plaques-de-cuisson?1261=2379%7C2380&1274=2392&r_lowestPrice=394.4-1026.6&sort=price",
    "frigo": "https://ledenicheur.fr/c/refrigerateurs?1304=2405&3666=3468&r_1265=141.8-1243&r_1426=1433-1931&r_1428=0-619&r_lowestPrice=501-1262.8&sort=price",
}
PROMOS = {
    "lego": "https://ledenicheur.fr/actu/top-promo?brand=2624",
    "top promo": "https://ledenicheur.fr/actu/top-promo?category=523%7C530%7C580",
}
FICHE = "https://ledenicheur.fr/product.php?p=13308334"

ZW = {ord(c): None for c in "\u200b\u200c\u200d\u2060\u2063\ufeff"}
RE_PRIX = re.compile(r"^(\d[\d\s\u202f\u00a0]*,\d{2})\s*€$")
RE_PCT = re.compile(r"-\s?\d+\s?%")
RE_COMPTE = re.compile(r"Résultats incluant[^\n]{0,40}")
RE_MINMAX = re.compile(r"Min\s*:\s*[\d\s\u202f\u00a0,]+€\s*\|\s*Max\s*:\s*[\d\s\u202f\u00a0,]+€")
JS_TUILES = r"""() => Array.from(document.querySelectorAll('a[href*="product.php?p="]')).map(a => {
  const idOf = x => ((x.getAttribute('href') || '').match(/p=(\d+)/) || [])[1];
  let texte = a.innerText || '';
  let c = a;
  for (let i = 0; i < 3 && c.parentElement && !/€/.test(texte); i++) {
    c = c.parentElement;
    const ids = new Set(Array.from(c.querySelectorAll('a[href*="product.php?p="]')).map(idOf));
    if (ids.size > 1) break;
    texte = c.innerText;
  }
  return {id: idOf(a), nom: a.innerText || '', texte: texte};
})"""


def lignes(t):
    return [x.strip() for x in (t or "").translate(ZW).split("\n") if x.strip()]


def lire_tuiles(page):
    tuiles = {}
    for it in page.evaluate(JS_TUILES):
        if not it["id"]:
            continue
        l = lignes(it["texte"])
        nom = (lignes(it["nom"]) or ["?"])[0]
        prix = [m.group(1) for x in l for m in [RE_PRIX.match(x)] if m]
        pcts = RE_PCT.findall(" ".join(l))
        if it["id"] not in tuiles or (prix and not tuiles[it["id"]]["prix"]):
            tuiles[it["id"]] = {"nom": nom, "prix": prix, "pcts": pcts}
    return tuiles


with sync_playwright() as p:
    try:
        nav = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        nav = p.chromium.launch(headless=True)
    page = nav.new_page()
    premiere = {}

    for nom, url in RECHERCHES.items():
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            corps = page.inner_text("body")
            t = lire_tuiles(page)
            if nom == "pyrolyse":
                premiere = t
            vus = list(t.values())[:8]
            print(f"\n=== {nom} : {len(t)} produits lus")
            print("  compteur :", RE_COMPTE.findall(corps)[:1])
            print("  8 premiers prix :", [v["prix"][0] if v["prix"] else "?" for v in vus])
            print("  3 premiers :", [v["nom"][:35] for v in vus[:3]])
        except Exception as e:
            print(f"\n=== {nom} : ERREUR {str(e)[:100]}")

    try:
        page.goto(RECHERCHES["pyrolyse"] + "&page=2", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        t2 = lire_tuiles(page)
        communs = len(set(t2) & set(premiere))
        print(f"\n=== PAGINATION (pyrolyse, page=2) : {len(t2)} produits, {communs} déjà vus en page 1")
        print("  3 premiers :", [v["nom"][:35] for v in list(t2.values())[:3]])
    except Exception as e:
        print(f"\n=== PAGINATION : ERREUR {str(e)[:100]}")

    for nom, url in PROMOS.items():
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
            t = lire_tuiles(page)
            avec = sum(1 for v in t.values() if v["pcts"])
            print(f"\n=== PROMO {nom} : {len(t)} produits, {avec} avec un % dans la tuile")
            for pid, v in list(t.items())[:10]:
                print(f"  {pid} | {v['nom'][:45]} | prix {v['prix']} | % {v['pcts']}")
            print("  lignes avec % :", [x for x in lignes(page.inner_text("body")) if "%" in x][:6])
        except Exception as e:
            print(f"\n=== PROMO {nom} : ERREUR {str(e)[:100]}")

    try:
        page.goto(FICHE, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        corps = " ".join(page.inner_text("body").split())
        print("\n=== FICHE (historique) :", RE_MINMAX.findall(corps)[:2])
    except Exception as e:
        print(f"\n=== FICHE : ERREUR {str(e)[:100]}")
    nav.close()
