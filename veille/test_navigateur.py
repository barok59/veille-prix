import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URLS = [
    "https://www.electromenager-compare.com/four-ELEEOF6P46RX-ELECTROLUX-EOF6P46RX.htm",
    "https://www.electromenager-compare.com/four-ELEEOB8S39Z2024-ELECTROLUX-EOB8S39Z-2024.htm",
    "https://www.bonne-promo.com/prix/20776/electrolux-eof6p46rx-four",
    "https://ledenicheur.fr/s/four-vapeur-electrolux/",
    "https://www.auchan.fr/bosch-refrigerateur-1-porte-60cm-324l-ksv33vlep/pr-81828b9d-274d-46aa-9f4f-7357235f4ccc",
    "https://www.but.fr/produits/4242005205707/Refrigerateur-1-Porte-Bosch-Ksv33vlep-324-L-Inox.html",
    "https://www.conforama.fr/gros-electromenager/cuisson/four-encastrable/electrolux---four-vapeur-70l-60cm-noir-eob8s39z---serie-800/p/J53633547",
    "https://www.carrefour.fr/p/four-vapeur-electrolux-eob8s39z-7332543842056",
    "https://www.bricomarche.com/p/four-integrable-72l-60cm-pyrolyse-inox-eof6p46rx/7333394114002",
]
RE_PRIX = re.compile(r"\d[\d\s\u202f\u00a0]*[,.]\d{2}\s?€|\d[\d\s\u202f\u00a0]*\s?€")

with sync_playwright() as p:
    try:
        nav = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        nav = p.chromium.launch(headless=True)
    page = nav.new_page()
    for url in URLS:
        try:
            rep = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            texte = BeautifulSoup(page.content(), "html.parser").get_text(" ", strip=True)
            prix = [m.strip() for m in RE_PRIX.findall(texte)[:8]]
            print(f"\n{url[:75]}\n  HTTP {rep.status if rep else '?'} | {page.title()[:60]!r} | {prix}")
        except Exception as e:
            print(f"\n{url[:75]}\n  ERREUR {str(e)[:80]}")
    nav.close()
