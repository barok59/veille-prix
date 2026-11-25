import datetime

from discord import envoyer_long

SEUIL = 3


def maintenant():
    # Précision à l'heure : limite le nombre de commits de l'historique
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:00:00+00:00")


def _parse(iso):
    try:
        return datetime.datetime.fromisoformat(iso)
    except Exception:
        return None


def fmt(iso):
    d = _parse(iso) if iso else None
    if d is None:
        return "jamais"
    try:
        from zoneinfo import ZoneInfo
        d = d.astimezone(ZoneInfo("Europe/Paris"))
    except Exception:
        pass
    return d.strftime("%d/%m %Hh")


def ancien_depuis(iso):
    """Âge en heures, ou None."""
    d = _parse(iso) if iso else None
    if d is None:
        return None
    return (datetime.datetime.now(datetime.timezone.utc) - d).total_seconds() / 3600


def suivre(historique, cle, ok, libelle, evenements, seuil=SEUIL):
    """Met à jour l'état d'une source et ajoute un message à `evenements` si besoin."""
    sante = historique.setdefault("_sante", {})
    e = sante.setdefault(cle, {"echecs": 0, "alerte": False, "dernier_ok": None})
    e["libelle"] = libelle
    if ok:
        e["dernier_ok"] = maintenant()
        e["echecs"] = 0
        if e["alerte"]:
            e["alerte"] = False
            evenements.append(f"✅ Source rétablie : {libelle}")
    else:
        e["echecs"] += 1
        if e["echecs"] >= seuil and not e["alerte"]:
            e["alerte"] = True
            evenements.append(f"⚠️ Source muette depuis {e['echecs']} passages : {libelle} "
                              f"(dernier succès : {fmt(e.get('dernier_ok'))})")


def signaler(evenements):
    if evenements:
        envoyer_long("🩺 Santé de l'agent :\n" + "\n".join(evenements))
