import sys, json, yaml, pathlib
from dealabs import charger_deals, filtrer
from discord import envoyer


def veille_dealabs(cfg, historique):
    deals = charger_deals()
    nouveautes = []
    cibles = [(p["nom"], p["mots_cles"]) for p in cfg["produits"]]
    cibles += [(c["nom"], c["mots_cles"]) for c in cfg.get("categories", [])]
    for nom, mots in cibles:
        for deal in filtrer(deals, mots):
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
            note = " ⚠️ marketplace : vérifie le vendeur" if "marketplace" in ou.lower() else ""
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


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dealabs"
    hist = pathlib.Path(f"data/history_{mode}.json")
    historique = json.loads(hist.read_text()) if hist.exists() else {}
    cfg = yaml.safe_load(open("config/electromenager.yaml"))
    if mode == "dealabs":
        veille_dealabs(cfg, historique)
    elif mode == "prix":
        veille_prix(cfg, historique)
    else:
        print(f"Mode inconnu : {mode} (utiliser 'dealabs' ou 'prix')")
    hist.parent.mkdir(exist_ok=True)
    hist.write_text(json.dumps(historique, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
