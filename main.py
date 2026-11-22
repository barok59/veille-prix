import json, yaml, pathlib
from dealabs import chercher
from discord import envoyer

HIST = pathlib.Path("data/history.json")

def main():
    historique = json.loads(HIST.read_text()) if HIST.exists() else {}
    cfg = yaml.safe_load(open("config/electromenager.yaml"))
    nouveautes = []
    for p in cfg["produits"]:
        for mot in p["mots_cles"]:
            for deal in chercher(mot):
                if deal["lien"] not in historique:
                    historique[deal["lien"]] = deal["titre"]
                    nouveautes.append(f"**{p['nom']}** : {deal['titre']}\n{deal['lien']}")
    if nouveautes:
        envoyer("🔔 Nouveautés détectées :\n\n" + "\n\n".join(nouveautes))
    HIST.parent.mkdir(exist_ok=True)
    HIST.write_text(json.dumps(historique, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
