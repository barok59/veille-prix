from playwright.sync_api import sync_playwright

URL = "https://www.connexion.fr/gros-electromenager/lave-vaisselle/encastrable/779-111677.html"

with sync_playwright() as p:
    try:
        nav = p.chromium.launch(channel="chrome", headless=False)
    except Exception:
        nav = p.chromium.launch(headless=False)
    page = nav.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    html = page.content()
    for cible in ["699.00", "649"]:
        i = html.find(cible)
        print(f"\n--- contexte de {cible} ---")
        print(html[max(0, i - 250): i + 120].replace("\n", " "))
    nav.close()
