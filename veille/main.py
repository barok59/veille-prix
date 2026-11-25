import datetime
import json
import os
import pathlib
import re
import sys

import yaml

from dealabs import charger_deals, filtrer
from discord import envoyer


def veille_dealabs(cfg, historique):
    deals = charger_deals()
    nouveautes = []
    cibles = [(p["nom"], p["mots_cles"], [], "texte") for p in cfg["produits"]]
    cibles += [(c["nom"], c["mots_cles"], c.get("exclure", []), "titre")
               for c in cfg.get("categories", [])]
    for nom, mots, excl, champ in cibles:
        for deal in filtrer(deals, mots, excl, champ):
            if deal["lien"] not in historique:
                historique[deal["lien"]] = deal["titre"]
                nouveautes.append(f"**{nom}** : {deal['titre']}\n{deal['lien']}")
    if nouveautes:
        envoyer("🔔 Deal Dealabs :\n\n" + "\n\n".join(nouveautes))
    else:
        print("Dealabs : rien de nouveau.")


def veille_prix(cfg, historique):
    from prix import lire_prix_sources
    memoire = historique.setdefault("_prix", {})
    sources = [dict(s, produit=p) for p in cfg["produits"] for s in p.get("sources", [])]
    prix = lire_prix_sources(sources)
    alertes = []
    for s in sources:
        p = s["produit"]
        valeur, vendeur = prix.get(s["url"], (None, None))
        if valeur is None:
            continue
        cle = f"{p['id']}|{s['site']}"
        ancien = memoire.get(cle, {})
        ref = p.get("prix_reference")
        if ref is not None and valeur < ref and valeur != ancien.get("dernier_notifie"):
            ou = vendeur or s["site"]
            note = (" ⚠️ vendeur tiers : vérifie le vendeur"
                    if any(m in ou.lower() for m in ("marketplace", "ebay")) else "")
            alertes.append(f"**{p['nom']}** : {valeur:.2f} € chez {ou} "
                           f"(référence {ref:.2f} €){note}\n{s['url']}")
            ancien["dernier_notifie"] = valeur
        ancien["dernier_prix"] = valeur
        ancien["plus_bas"] = min(valeur, ancien.get("plus_bas", valeur))
        memoire[cle] = ancien
    if alertes:
        envoyer("💶 Baisse de prix :\n\n" + "\n\n".join(alertes))
    else:
        print("Prix : aucune baisse sous la référence.")


def veille_recap(cfg, historique):
    src = pathlib.Path("data/history_prix.json")
    memoire = json.loads(src.read_text()).get("_prix", {}) if src.exists() else {}
    precedent = historique.get("snapshot", {})
    snapshot, lignes = {}, []
    for p in cfg["produits"]:
        if "id" not in p:
            print(f"[recap] produit sans id ignoré : {p.get('nom', p)}")
            continue
        entrees = {k.split("|", 1)[1]: v for k, v in memoire.items()
                   if k.startswith(p["id"] + "|") and v.get("dernier_prix") is not None}
        if not entrees:
            lignes.append(f"• **{p['nom']}** : pas de prix suivi automatiquement")
            continue
        site, d = min(entrees.items(), key=lambda kv: kv[1]["dernier_prix"])
        actuel = d["dernier_prix"]
        plus_bas = min(v.get("plus_bas", v["dernier_prix"]) for v in entrees.values())
        snapshot[p["id"]] = actuel
        texte = f"• **{p['nom']}** : {actuel:.2f} € ({site})"
        ref = p.get("prix_reference")
        if ref:
            texte += f" | réf. {ref:.2f} € ({actuel - ref:+.2f} €)"
        texte += f" | plus bas vu : {plus_bas:.2f} €"
        avant = precedent.get(p["id"])
        if avant is not None:
            texte += f" | vs semaine dernière : {actuel - avant:+.2f} €"
        lignes.append(texte)
    jours = (cfg["deadline"] - datetime.date.today()).days
    envoyer(f"📊 Récap hebdo : il reste {jours} jours avant la deadline\n\n" + "\n".join(lignes))
    historique["snapshot"] = snapshot


def veille_equivalents(cfg, historique):
    from equivalents import lire_recherches
    recherches = [r for r in cfg.get("recherches", []) if r.get("url")]
    if not recherches:
        print("Équivalents : aucune recherche configurée (url vide).")
        return
    suivis = set()
    for p in cfg["produits"]:
        for s in p.get("sources", []):
            m = re.search(r"product\.php\?p=(\d+)", s["url"])
            if m:
                suivis.add(m.group(1))
    resultats = lire_recherches(recherches)
    base = historique.setdefault("recherches", {})
    alertes, demarrees, signales = [], [], set()
    for r in recherches:
        courant = resultats.get(r["nom"])
        if not courant:
            print(f"[equiv] {r['nom']} : aucune donnée lue, ignorée")
            continue
        connu = base.get(r["nom"])
        if connu is None:
            base[r["nom"]] = {pid: {"nom": v["nom"], "prix": v["prix"]} for pid, v in courant.items()}
            demarrees.append(f"{r['nom']} ({len(courant)} modèles)")
            continue
        pmax = r.get("prix_max")
        for pid, v in courant.items():
            prix = v["prix"]
            lien = f"https://ledenicheur.fr/product.php?p={pid}"
            dans_budget = pmax is None or prix is None or prix <= pmax
            if pid not in suivis and pid not in signales and dans_budget:
                if pid not in connu:
                    p_txt = f"{prix:.2f} €" if prix is not None else "prix non lu"
                    alertes.append(f"🆕 **{r['nom']}** : {v['nom']} à {p_txt}\n{lien}")
                    signales.add(pid)
                else:
                    ancien = connu[pid].get("prix")
                    if prix is not None and ancien and prix <= ancien * 0.90:
                        alertes.append(f"📉 **{r['nom']}** : {v['nom']} {ancien:.2f} € → {prix:.2f} € "
                                       f"({(prix / ancien - 1) * 100:.0f} %)\n{lien}")
                        signales.add(pid)
            garde = prix if prix is not None else connu.get(pid, {}).get("prix")
            connu[pid] = {"nom": v["nom"], "prix": garde}
    if demarrees:
        envoyer("🔎 Surveillance des équivalents démarrée : " + ", ".join(demarrees))
    if alertes:
        reste = len(alertes) - 8
        envoyer("\n\n".join(alertes[:8]) + (f"\n\n…et {reste} autre(s)" if reste > 0 else ""))
    elif not demarrees:
        print("Équivalents : rien de nouveau.")


def veille_promos(cfg, historique):
    from promos import collecter
    promos = [r for r in cfg.get("promos", []) if r.get("url")]
    if not promos:
        print("Promos : aucune page configurée (url vide).")
        return
    debug = os.environ.get("PROMOS_DEBUG") == "1"
    base = historique.setdefault("promos", {})
    alertes, demarrees = collecter(promos, base, debug=debug)
    if debug:
        print("[promos] mode diagnostic : rien envoyé, rien sauvegardé.")
        return
    if demarrees:
        envoyer("🏷️ Surveillance des promos démarrée : " + ", ".join(demarrees))
    if alertes:
        reste = len(alertes) - 6
        envoyer("\n\n".join(alertes[:6]) + (f"\n\n…et {reste} autre(s)" if reste > 0 else ""))
    elif not demarrees:
        print("Promos : rien de nouveau.")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dealabs"
    hist = pathlib.Path(f"data/history_{mode}.json")
    historique = json.loads(hist.read_text()) if hist.exists() else {}
    with open("config/electromenager.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    modes = {"dealabs": veille_dealabs, "prix": veille_prix, "recap": veille_recap,
             "equivalents": veille_equivalents, "promos": veille_promos}
    if mode not in modes:
        print(f"Mode inconnu : {mode} (utiliser {', '.join(modes)})")
        return
    modes[mode](cfg, historique)
    if mode == "promos" and os.environ.get("PROMOS_DEBUG") == "1":
        return
    hist.parent.mkdir(exist_ok=True)
    hist.write_text(json.dumps(historique, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
