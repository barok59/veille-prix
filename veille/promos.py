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


def _nouvelle_page(nav, page):
    """Ferme la page courante (si possible) et en ouvre une neuve."""
    try:
        page.close()
    except Exception:
        pass
    return nav.new_page()


def collecter(promos, base, debug=False, max_fiches=12, etat=None):
    """Modifie `base` en place. `etat[nom]` = True si la page a été lue.
    Renvoie (alertes, demarrees)."""
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
                if etat is not None:
                    etat[r["nom"]] = False
                page = _nouvelle_page(nav, page)
                continue
            print(f"[promos] {r['nom']} : {len(tuiles)} offres lues")
            if etat is not None:
                etat[r["nom"]] = bool(tuiles)
            if not tuiles:
                continue
            connu = base.get(r["nom"])
            if debug:
                a_traiter = [(pid, v, None) for pid, v in list(tuiles.items())[:3]]
            elif connu is None:
                base[r["nom"]] = {pid: {"nom": v["nom"], "prix": v["prix"]}
                                  for pid, v in tuiles.items()}
                demarrees.append(f"{r['nom']} ({len(tuiles)} offres)")
                continue
            else:
                # Si une offre connue remonte, on relève sa référence
                for pid, v in tuiles.items():
                    if pid in connu and v["prix"] is not None:
                        ancien = connu[pid].get("prix")
                        if ancien and v["prix"] > ancien:
                            connu[pid]["prix"] = v["prix"]
                a_traiter = []
                for pid, v in tuiles.items():
                    if pid not in connu:
                        a_traiter.append((pid, v, None))
                    else:
                        ancien = connu[pid].get("prix")
                        if v["prix"] is not None and ancien and v["prix"] <= ancien * 0.90:
                            a_traiter.append((pid, v, ancien))
                a_traiter = a_traiter[:max_fiches]
            seuil = float(r.get("pourcent_reduc", 0))
            for pid, v, ancien in a_traiter:
                if pid not in cache:
                    try:
                        cache[pid] = lire_min_max(page, pid)
                    except Exception as e:
                        print(f"[promos]   fiche {pid} -> ERREUR {str(e)[:80]}")
                        cache[pid] = (None, None)
                        page = _nouvelle_page(nav, page)
                mini, maxi = cache[pid]
                prix = v["prix"]
                remise = (1 - prix / maxi) * 100 if (prix is not None and maxi) else None
                txt = f"{remise:.0f} %" if remise is not None else "?"
                type_ = "baisse" if ancien else "nouveau"
                print(f"[promos]   [{type_}] {v['nom'][:45]} | prix {prix} | min {mini} | max {maxi} | remise {txt}")
                if not debug:
                    if remise is not None and remise >= seuil:
                        suite = f" (en baisse depuis {ancien:.2f} €)" if ancien else ""
                        alertes.append(
                            f"🏷️ **{r['nom']}** : {v['nom']} à {prix:.2f} € "
                            f"(-{remise:.0f} % vs prix max récent {maxi:.2f} €){suite}\n"
                            f"https://ledenicheur.fr/product.php?p={pid}")
                    connu[pid] = {"nom": v["nom"], "prix": prix}
        nav.close()
    return alertes, demarrees
