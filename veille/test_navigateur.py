import re
from playwright.sync_api import sync_playwright

IDS = ["15832204", "6922396", "5600701", "7574984", "3708412"]
RE_DES = re.compile(r"D[èe]s\s+([\d\s\u202f\u00a0]+[,.]\d{2})\s?€")

with sync_playwright() as p:
    try:
        nav = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        nav = p.chromium.launch(headless=True)
    page = nav.new_page()
    for pid in IDS:
        url = f"https://ledenicheur.fr/product.php?p={pid}"
        try:
            rep = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            titre = page.title()
            try:
                meta = page.locator('meta[name="description"]').first.get_attribute("content", timeout=3000) or ""
            except Exception:
                meta = ""
            m = RE_DES.search(titre) or RE_DES.search(meta)
            print(f"\n[{pid}] HTTP {rep.status if rep else '?'}")
            print(f"  titre : {titre[:90]}")
            print(f"  prix 'dès' : {m.group(1) if m else 'non trouvé'}")
            corps = page.inner_text("body")
            i = corps.find("Comparer les prix")
            extrait = " | ".join(l.strip() for l in corps[i:i + 700].split("\n") if l.strip())
            print(f"  offres : {extrait[:400]}")
        except Exception as e:
            print(f"\n[{pid}] ERREUR {str(e)[:100]}")
    nav.close()
