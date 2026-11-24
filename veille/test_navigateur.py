from playwright.sync_api import sync_playwright

URL = "https://ledenicheur.fr/actu/top-promo?category=1183%7C523%7C530%7C580"
JS = """() => Array.from(document.querySelectorAll('a[href*="product.php?p="]')).slice(0, 6).map(a => {
  const niveaux = [];
  let c = a;
  for (let i = 0; i < 3 && c.parentElement; i++) { c = c.parentElement; niveaux.push(c.innerText); }
  return {href: a.getAttribute('href'), lien: a.innerText, niveaux};
})"""

with sync_playwright() as p:
    try:
        nav = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        nav = p.chromium.launch(headless=True)
    page = nav.new_page()
    rep = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(5000)
    print("HTTP", rep.status if rep else "?", "|", page.title()[:80])
    for it in page.evaluate(JS):
        print("\n", it["href"])
        print("  lien   :", " | ".join(it["lien"].split())[:150])
        for k, n in enumerate(it["niveaux"], 1):
            print(f"  niveau {k}:", " | ".join(n.split())[:200])
    corps = page.inner_text("body")
    print("\nnombre de '%' dans la page :", corps.count("%"))
    nav.close()
