import sys, json, yaml, pathlib
from dealabs import charger_deals, filtrer
from discord import envoyer

HIST = pathlib.Path("data/history.json")

def veille_dealabs(cfg, historique):
    deals = charger_deals()
    nouveautes = []
    for p in cfg["produits"]:
        for deal in filtrer(deals, p["mots_cles"]):
            if deal["lien"] not in historique:
                historique[deal["lien"]] = deal["titre"]
                nouveautes.append(f"**{p['nom']}** : {deal['titre']}\n{deal['lien']}")
    if nouveautes:
        envoyer("🔔 Deal Dealabs :\n\n" + "\n\n".join(nouveautes))
    else:
        print("Dealabs : rien de nouveau.")

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dealabs"
    historique = json.loads(HIST.read_text()) if HIST.exists() else {}
    cfg = yaml.safe_load(open("config/electromenager.yaml"))
    if mode == "dealabs":
        veille_dealabs(cfg, historique)
    HIST.parent.mkdir(exist_ok=True)
    HIST.write_text(json.dumps(historique, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
