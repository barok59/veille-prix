import copy
import datetime
import json
import os
import pathlib
import re
import sys

import yaml

from dealabs import charger_deals, filtrer
from discord import envoyer_long
from sante import ancien_depuis, fmt, signaler, suivre


def _charger(mode):
    f = pathlib.Path(f"data/history_{mode}.json")
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except Exception:
        return {}


def _ecrire(chemin, historique):
    chemin.parent.mkdir(exist_ok=True)
    chemin.write_text(json.dumps(historique, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- Dealabs
def veille_dealabs(cfg, historique, evenements):
    deals = charger_deals()
    suivre(historique, "dealabs:flux", len(deals) > 0, "Flux Dealabs (rss/tous)", evenements)
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
        envoyer_long("🔔 Deal Dealabs :\n\n" + "\n\n".join(nouveautes))
    else:
        print("Dealabs : rien de nouveau.")


# ------------------------------------------------------------------- Prix
def veille_prix(cfg, historique, evenements):
    from prix import est_tiers, lire_prix_sources
    memoire = historique.setdefault("_prix", {})
    sources = [dict(s, produit=p) for p in cfg["produits"] for s in p.get("sources", [])]
    resultats = lire_prix_sources(sources)
    alertes = []
    for s in sources:
        p = s["produit"]
        r = resultats.get(s["url"]) or {}
        valeur = r.get("prix")
        suivre(historique, f"prix:{p['id']}|{s['site']}", valeur is not None,
               f"{p['nom']} ({s['site']})", evenements)
        if valeur is None:
            continue
        vendeur, pe, ve = r.get("vendeur"), r.get("prix_enseigne"), r.get("vendeur_enseigne")
        cle = f"{p['id']}|{s['site']}"
        ancien = memoire.get(cle, {})
        ref = p.get("prix_reference")
        if ref is not None:
            decl_total = valeur < ref and valeur != ancien.get("dernier_notifie")
            decl_ens = pe is not None and pe < ref and pe != ancien.get("dernier_notifie_enseigne")
            if decl_total or decl_ens:
                ou = vendeur or s["site"]
                texte = f"**{p['nom']}** : {valeur:.2f} € chez {ou} (référence {ref:.2f} €)"
                if est_tiers(vendeur):
                    texte += " ⚠️ vendeur tiers : vérifie le vendeur"
                if pe is not None and abs(pe - valeur) > 0.01:
                    texte += (f"\n   ↳ meilleur prix en enseigne : {pe:.2f} € chez {ve or s['site']} "
                              f"({pe - ref:+.2f} € vs référence)")
                elif pe is None and r.get("vendeurs_lus"):
                    texte += "\n   ↳ aucune enseigne listée sur cette fiche"
                alertes.append(texte + f"\n{s['url']}")
            if valeur < ref:
                ancien["dernier_notifie"] = valeur
            if pe is not None and pe < ref:
                ancien["dernier_notifie_enseigne"] = pe
        ancien.update({"dernier_prix": valeur, "vendeur": vendeur, "prix_enseigne": pe,
                       "vendeur_enseigne": ve, "vendeurs_lus": r.get("vendeurs_lus", False)})
        ancien["plus_bas"] = min(valeur, ancien.get("plus_bas", valeur))
        memoire[cle] = ancien
    if alertes:
        envoyer_long("💶 Baisse de prix :\n\n" + "\n\n".join(alertes))
    else:
        print("Prix : aucune baisse sous la référence.")


# ------------------------------------------------------------------ Récap
def _lignes_panier(cfg, actuels, refs, noms):
    ids = [i for i in actuels if i in refs]
    if not ids:
        return []
    tot_a = sum(actuels[i] for i in ids)
    tot_r = sum(refs[i] for i in ids)
    lignes = [f"🧺 Panier ({len(ids)} produits) : {tot_a:.2f} € aux meilleurs prix vus, "
              f"contre {tot_r:.2f} € à tes références ({tot_a - tot_r:+.2f} €)"]
    paniers = cfg.get("paniers", [])
    for pal in paniers:
        ids_p = [i for i in pal.get("produits", []) if i in refs]
        if not ids_p:
            continue
        total = sum(refs[i] for i in ids_p)
        seuil, remise = pal["seuil"], pal.get("remise", 0)
        if total >= seuil:
            lignes.append(f"🏪 {pal['nom']} : {total:.2f} € de références, seuil de {seuil} € atteint "
                          f"(marge {total - seuil:.2f} €, remise {remise} €)")
            for i in ids_p:
                if i in actuels and actuels[i] < refs[i]:
                    eco = refs[i] - actuels[i]
                    if total - refs[i] < seuil:
                        lignes.append(f"   ↳ {noms[i]} ailleurs à {actuels[i]:.2f} € : économie {eco:.2f} € "
                                      f"mais remise perdue → net {eco - remise:+.2f} €")
                    else:
                        lignes.append(f"   ↳ {noms[i]} ailleurs à {actuels[i]:.2f} € : "
                                      f"économie {eco:.2f} €, remise conservée")
        else:
            lignes.append(f"🏪 {pal['nom']} : {total:.2f} € de références, "
                          f"il manque {seuil - total:.2f} € pour le seuil de {seuil} € (remise {remise} €)")
    if paniers:
        lignes.append("ℹ️ Les paliers se calculent sur tes prix de référence, pas sur les prix du marchand.")
    return lignes


def _lignes_sante():
    pannes, retards = [], []
    for mode in ("dealabs", "prix", "equivalents", "promos"):
        for cle, e in _charger(mode).get("_sante", {}).items():
            if e.get("alerte"):
                pannes.append(f"• {e.get('libelle', cle)} : muette depuis {e.get('echecs', '?')} passages "
                              f"(dernier succès : {fmt(e.get('dernier_ok'))})")
            elif cle.startswith("mode:"):
                age = ancien_depuis(e.get("dernier_ok"))
                if age is not None and age > 36:
                    retards.append(f"• mode {cle[5:]} : aucun passage réussi depuis {age:.0f} h")
    if not pannes and not retards:
        return ["🩺 Sources : tout répond"]
    return ["🩺 Santé de l'agent :"] + pannes + retards


def veille_recap(cfg, historique, evenements):
    memoire = _charger("prix").get("_prix", {})
    precedent = historique.get("snapshot", {})
    snapshot, lignes = {}, []
    actuels, refs, noms = {}, {}, {}
    for p in cfg["produits"]:
        if "id" not in p:
            print(f"[recap] produit sans id ignoré : {p.get('nom', p)}")
            continue
        noms[p["id"]] = p["nom"]
        ref = p.get("prix_reference")
        if ref:
            refs[p["id"]] = ref
        entrees = {k.split("|", 1)[1]: v for k, v in memoire.items()
                   if k.startswith(p["id"] + "|") and v.get("dernier_prix") is not None}
        if not entrees:
            lignes.append(f"• **{p['nom']}** : pas de prix suivi automatiquement")
            continue
        site, d = min(entrees.items(), key=lambda kv: kv[1]["dernier_prix"])
        actuel = d["dernier_prix"]
        actuels[p["id"]] = actuel
        snapshot[p["id"]] = actuel
        plus_bas = min(v.get("plus_bas", v["dernier_prix"]) for v in entrees.values())
        vendeur = d.get("vendeur")
        texte = f"• **{p['nom']}** : {actuel:.2f} € ({site}{' / ' + vendeur if vendeur else ''})"
        if ref:
            texte += f" | réf. {ref:.2f} € ({actuel - ref:+.2f} €)"
        texte += f" | plus bas vu : {plus_bas:.2f} €"
        avant = precedent.get(p["id"])
        if avant is not None:
            texte += f" | vs semaine dernière : {actuel - avant:+.2f} €"
        ens = [(v["prix_enseigne"], s, v.get("vendeur_enseigne")) for s, v in entrees.items()
               if v.get("prix_enseigne") is not None]
        if ens:
            pe, se, ve = min(ens, key=lambda x: x[0])
            if abs(pe - actuel) > 0.01:
                texte += f"\n   ↳ enseigne : {pe:.2f} € ({ve or se})"
        elif any(v.get("vendeurs_lus") for v in entrees.values()):
            texte += "\n   ↳ aucune enseigne listée"
        lignes.append(texte)
    jours = (cfg["deadline"] - datetime.date.today()).days
    corps = [f"📊 Récap hebdo : il reste {jours} jours avant la deadline", ""] + lignes
    panier = _lignes_panier(cfg, actuels, refs, noms)
    if panier:
        corps += [""] + panier
    corps += [""] + _lignes_sante()
    envoyer_long("\n".join(corps))
    historique["snapshot"] = snapshot


# ------------------------------------------------------------ Équivalents
def veille_equivalents(cfg, historique, evenements):
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
    for r in recherches:
        suivre(historique, f"equiv:{r['nom']}", bool(resultats.get(r["nom"])),
               f"Recherche « {r['nom']} »", evenements)
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
        envoyer_long("🔎 Surveillance des équivalents démarrée : " + ", ".join(demarrees))
    if alertes:
        reste = len(alertes) - 8
        envoyer_long("\n\n".join(alertes[:8]) + (f"\n\n…et {reste} autre(s)" if reste > 0 else ""))
    elif not demarrees:
        print("Équivalents : rien de nouveau.")


# ----------------------------------------------------------------- Promos
def veille_promos(cfg, historique, evenements):
    from promos import collecter
    promos = [r for r in cfg.get("promos", []) if r.get("url")]
    if not promos:
        print("Promos : aucune page configurée (url vide).")
        return
    debug = os.environ.get("PROMOS_DEBUG") == "1"
    base = historique.setdefault("promos", {})
    etat = {}
    alertes, demarrees = collecter(promos, base, debug=debug, etat=etat)
    if debug:
        print("[promos] mode diagnostic : rien envoyé, rien sauvegardé.")
        return
    for r in promos:
        suivre(historique, f"promos:{r['nom']}", etat.get(r["nom"], False),
               f"Promos « {r['nom']} »", evenements)
    if demarrees:
        envoyer_long("🏷️ Surveillance des promos démarrée : " + ", ".join(demarrees))
    if alertes:
        reste = len(alertes) - 6
        envoyer_long("\n\n".join(alertes[:6]) + (f"\n\n…et {reste} autre(s)" if reste > 0 else ""))
    elif not demarrees:
        print("Promos : rien de nouveau.")


# ------------------------------------------------------------------- Main
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
    debug = mode == "promos" and os.environ.get("PROMOS_DEBUG") == "1"
    avant = copy.deepcopy(historique)
    evenements = []
    try:
        modes[mode](cfg, historique, evenements)
    except Exception as e:
        print(f"[erreur] mode {mode} : {type(e).__name__}: {str(e)[:200]}")
        if not debug:
            historique = avant  # on n'enregistre pas un état à moitié modifié
            suivre(historique, f"mode:{mode}", False,
                   f"mode {mode} (plantage {type(e).__name__})", evenements)
            _ecrire(hist, historique)
            try:
                signaler(evenements)
            except Exception:
                pass
        raise
    if debug:
        return
    suivre(historique, f"mode:{mode}", True, f"mode {mode}", evenements)
    _ecrire(hist, historique)
    signaler(evenements)


if __name__ == "__main__":
    main()
