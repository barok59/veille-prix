import re
from playwright.sync_api import sync_playwright

PAGES = {
    "pyrolyse": "https://ledenicheur.fr/c/fours-encastres?559=120602",
    "vapeur": "https://ledenicheur.fr/c/fours-encastres?559=120603",
    "plaque": "https://ledenicheur.fr/c/plaques-de-cuisson?1261=2379%7C2380&1274=2392",
    "frigo": "https://ledenicheur.fr/c/refrigerateurs?1304=2405&3666=3468&r_1265=114.4-1243&r_1428=0-619",
}
TOP = "https://ledenicheur.fr/actu/top-promo?category=1183%7C523%7C530%7C580"
ZW = {ord(c): None for c in "\u200b\u200c\u200d\u2060\u2063\ufeff"}
RE_COMPTE = re.compile(r"[^\n]{0,30}\d[\d\s\u202f\u00a0]*\s+(?:produits|résultats|offres)[^\n]{0,20}")
JS_TUILES = """() => Array.from(document.querySelectorAll('a[href*="product.php?p="]')).slice(0, 6).map(a => {
  const niveaux = []; let c = a;
  for (let i = 0; i < 3 && c.parentElement; i++) { c = c.parentElement; niveaux.push(c.innerText); }
  return {href: a.getAttribute('href'), lien: a.innerText, niveaux};
})"""


def propre(t):
    return " | ".join(x.strip() for x in (t or "").translate(ZW).split("\n") if x.strip())


with sync_playwright() as p:
    try:
        nav = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        nav = p.chromium.launch(headless=True)
    page = nav.new_page()

    for nom, url in PAGES.items():
        try:
            rep = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            corps = page.inner_text("body")
            tuiles = page.locator('a[href*="product.php?p="]')
            print(f"\n=== {nom} : HTTP {rep.status if rep else '?'} | {tuiles.count()} tuiles")
            print("  url finale :", page.url)
            print("  compteurs  :", [propre(c)[:60] for c in RE_COMPTE.findall(corps)[:3]])
            try:
                print("  tri        :", page.locator("select option").all_inner_texts()[:8])
            except Exception:
                pass
            for i in range(min(tuiles.count(), 5)):
                print("   -", propre(tuiles.nth(i).inner_text())[:150])
        except Exception as e:
            print(f"\n=== {nom} : ERREUR {str(e)[:100]}")

    try:
        rep = page.goto(TOP, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)
        print(f"\n=== TOP PROMO : HTTP {rep.status if rep else '?'} | {page.title()[:60]}")
        for it in page.evaluate(JS_TUILES):
            print("\n ", it["href"])
            print("   lien   :", propre(it["lien"])[:150])
            for k, n in enumerate(it["niveaux"], 1):
                print(f"   niveau {k}:", propre(n)[:200])
        corps = page.inner_text("body")
        print("\n  '%' dans la page :", corps.count("%"), "| '€' :", corps.count("€"))
    except Exception as e:
        print(f"\n=== TOP PROMO : ERREUR {str(e)[:100]}")
    nav.close()
