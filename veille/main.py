import json, yaml, pathlib
from dealabs import charger_deals, filtrer
from discord import envoyer

HIST = pathlib.Path("data/history.json")

def main():
    historique = json.loads(HIST.read_text()) if HIST.exists() else {}
    cfg = yaml.safe_load(open("config/electromenager.yaml"))

    deals = charger_deals()
    for d in deals[:3]:
        print("[exemple]", d["titre"])

    nouveautes = []
    for p in cfg["produits"]:
        for deal in filtrer(deals, p["mots_cles"]):
            if deal["lien"] not in historique:
                historique[deal["lien"]] = deal["titre"]
                nouveautes.append(f"**{p['nom']}** : {deal['titre']}\n{deal['lien']}")

    if nouveautes:
        envoyer("🔔 Nouveautés détectées :\n\n" + "\n\n".join(nouveautes))
    else:
        print("Aucune nouveauté détectée.")

    HIST.parent.mkdir(exist_ok=True)
    HIST.write_text(json.dumps(historique, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
