from playwright.sync_api import sync_playwright

PAGES = [
    "https://ledenicheur.fr/c/fours-encastres",
    "https://ledenicheur.fr/c/lave-vaisselle",
    "https://ledenicheur.fr/c/hottes-aspirantes",
    "https://ledenicheur.fr/actu/top-promo",
]

with sync_playwright() as p:
    try:
        nav = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        nav = p.chromium.launch(headless=True)
    page = nav.new_page()
    for url in PAGES:
        try:
            rep = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            liens = page.locator('a[href*="product.php?p="]')
            n = liens.count()
            print(f"\n{url}\n  HTTP {rep.status if rep else '?'} | {page.title()[:70]!r} | {n} liens produit")
            for i in range(min(n, 5)):
                texte = " | ".join(t.strip() for t in liens.nth(i).inner_text().split("\n") if t.strip())
                print("   ", liens.nth(i).get_attribute("href"), "->", texte[:120])
        except Exception as e:
            print(f"\n{url}\n  ERREUR {str(e)[:100]}")
    nav.close()
