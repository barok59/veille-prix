import os
import re

from playwright.sync_api import sync_playwright

from equivalents import lire_tuiles

NB = r"[\d\s\u202f\u00a0]+(?:,\d{1,2})?"
RE_MINMAX = re.compile(rf"Min\s*:\s*({NB})\s*€\s*\|\s*Max\s*:\s*({NB})\s*€")


def _nombre(t):
    return float(re.sub(r"[\s\u202f\u00a0]", "", t).replace(",", "."))


def lire_min_max(page, pid):
    page.goto(f"https://ledenicheur.fr/product.php?p={pid}",
              wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    texte = " ".join(page.inner_text("body").split())
    m = RE_MINMAX.search(texte)
    if not m:
        brut = re.sub(r"<[^>]+>", " ", page.content())
        m = RE_MINMAX.search(" ".join(brut.split()))
    if not m:
        return None, None
    return _nombre(m.group(1)), _nombre(m.group(2))


def collecter(promos, base, debug=False, max_fiches=12):
    """Modifie `base` en place. Renvoie (alertes, demarrees)."""
    alertes, demarrees, cache = [], [], {}
    headless = os.environ.get("HEADLESS") == "1"
    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(channel="chrome", headless=headless)
        except Exception:
            nav = p.chromium.launch(headless=headless)
        page = nav.new_page()
        for r in promos:
            try:
                page.goto(r["url"], wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(5000)
                tuiles = lire_tuiles(page)
            except Exception as e:
                print(f"[promos] {r['nom']} -> ERREUR {str(e)[:100]}")
                continue
            print(f"[promos] {r['nom']} : {len(tuiles)} offres lues")
            if not tuiles:
                continue
            connu = base.get(r["nom"])
            if debug:
                a_traiter = list(tuiles.items())[:3]
            elif connu is None:
                base[r["nom"]] = {pid: {"nom": v["nom"], "prix": v["prix"]}
                                  for pid, v in tuiles.items()}
                demarrees.append(f"{r['nom']} ({len(tuiles)} offres)")
                continue
            else:
                a_traiter = [(pid, v) for pid, v in tuiles.items() if pid not in connu][:max_fiches]
            seuil = float(r.get("pourcent_reduc", 0))
            for pid, v in a_traiter:
                if pid not in cache:
                    try:
                        cache[pid] = lire_min_max(page, pid)
                    except Exception as e:
                        print(f"[promos]   fiche {pid} -> ERREUR {str(e)[:80]}")
                        cache[pid] = (None, None)
                mini, maxi = cache[pid]
                prix = v["prix"]
                remise = (1 - prix / maxi) * 100 if (prix is not None and maxi) else None
                txt = f"{remise:.0f} %" if remise is not None else "?"
                print(f"[promos]   {v['nom'][:45]} | prix {prix} | min {mini} | max {maxi} | remise {txt}")
                if not debug:
                    if remise is not None and remise >= seuil:
                        alertes.append(
                            f"🏷️ **{r['nom']}** : {v['nom']} à {prix:.2f} € "
                            f"(-{remise:.0f} % vs prix max récent {maxi:.2f} €)\n"
                            f"https://ledenicheur.fr/product.php?p={pid}")
                    connu[pid] = {"nom": v["nom"], "prix": prix}
        nav.close()
    return alertes, demarrees
