import os
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.sync_api import sync_playwright

TAILLE_PAGE = 44
ZW = {ord(c): None for c in "\u200b\u200c\u200d\u2060\u2063\ufeff"}
RE_PRIX = re.compile(r"^(\d[\d\s\u202f\u00a0]*,\d{2})\s*€$")
RE_TOTAL = re.compile(r"R[ée]sultats incluant\s+(\d[\d\s\u202f\u00a0]*)\s+produits", re.IGNORECASE)
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


def _nombre(t):
    return float(re.sub(r"[\s\u202f\u00a0]", "", t).replace(",", "."))


def _lignes(t):
    return [x.strip() for x in (t or "").translate(ZW).split("\n") if x.strip()]


def lire_tuiles(page, limite=None):
    """Renvoie {id: {nom, prix}} dans l'ordre de la page."""
    tuiles = {}
    for it in page.evaluate(JS_TUILES):
        pid = it["id"]
        if not pid:
            continue
        nom = (_lignes(it["nom"]) or ["?"])[0]
        prix_l = [_nombre(m.group(1)) for l in _lignes(it["texte"])
                  for m in [RE_PRIX.match(l)] if m]
        prix = min(prix_l) if prix_l else None
        cur = tuiles.get(pid)
        if cur is None:
            tuiles[pid] = {"nom": nom, "prix": prix}
        else:
            if cur["prix"] is None and prix is not None:
                cur["prix"] = prix
            if cur["nom"] == "?" and nom != "?":
                cur["nom"] = nom
    items = list(tuiles.items())
    return dict(items[:limite]) if limite else dict(items)


def _url_page(url, offset):
    u = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if k != "offset"]
    if offset:
        q.append(("offset", str(offset)))
    return urlunparse(u._replace(query=urlencode(q)))


def _lire_recherche(page, r):
    url = r["url"]
    pages_max = int(r.get("pages_max", 6))
    pmax = r.get("prix_max")
    trie = "sort=price" in url
    produits, total = {}, None
    for n in range(pages_max):
        page.goto(_url_page(url, n * TAILLE_PAGE), wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3500)
        if total is None:
            m = RE_TOTAL.search(page.inner_text("body"))
            total = int(re.sub(r"\D", "", m.group(1))) if m else None
        # Après les résultats, la page ajoute des suggestions : on ne garde que les résultats restants.
        limite = TAILLE_PAGE if total is None else min(TAILLE_PAGE, total - len(produits))
        if limite <= 0:
            break
        tuiles = lire_tuiles(page, limite)
        nouveaux = {k: v for k, v in tuiles.items() if k not in produits}
        prix = [v["prix"] for v in tuiles.values() if v["prix"] is not None]
        bas = f"{min(prix):.0f}" if prix else "?"
        haut = f"{max(prix):.0f}" if prix else "?"
        print(f"[equiv]   {r['nom']} page {n + 1} : {len(tuiles)} tuiles, "
              f"{len(nouveaux)} nouvelles, prix {bas} -> {haut} (total annoncé : {total})")
        if not nouveaux:
            break
        produits.update(nouveaux)
        if total is not None and len(produits) >= total:
            break
        if len(tuiles) < TAILLE_PAGE:
            break
        if trie and pmax is not None and prix and min(prix) > pmax:
            break
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
                res = _lire_recherche(page, r)
                print(f"[equiv] {r['nom']} : {len(res)} produits lus au total")
                resultats[r["nom"]] = res
            except Exception as e:
                print(f"[equiv] {r['nom']} -> ERREUR {str(e)[:100]}")
                try:
                    page.close()
                except Exception:
                    pass
                page = nav.new_page()
        nav.close()
    return resultats
