"""Outils locaux de Sentinelle : ils interrogent la vraie API api-virements sur l'EC2."""
import json
import subprocess
from collections import Counter

import httpx
from strands import tool

# Listes blanches : l'agent ne peut viser que ces services. Jamais d'URL ou de commande libre.
SERVICES = {"api-virements": "http://localhost:8080"}
CONTENEURS = {"api-virements": "api"}


@tool
def verifier_sante(service: str) -> dict:
    """Vérifie la santé d'un service de la Banque Atlas via ses sondes /health et /ready.

    Args:
        service: nom du service à vérifier, par exemple "api-virements".
    """
    base = SERVICES.get(service)
    if base is None:
        return {"erreur": f"service inconnu : {service}", "services_connus": list(SERVICES)}
    resultat = {"service": service}
    for sonde in ("health", "ready"):
        try:
            reponse = httpx.get(f"{base}/{sonde}", timeout=3)
            resultat[sonde] = reponse.status_code
        except httpx.HTTPError as exc:
            resultat[sonde] = f"injoignable ({type(exc).__name__})"
    return resultat


@tool
def lire_logs_erreurs(service: str, minutes: int = 15) -> dict:
    """Résume les erreurs récentes d'un service : nombre, répartition par code d'erreur et exemples.

    Args:
        service: nom du service, par exemple "api-virements".
        minutes: fenêtre d'analyse en minutes (entre 1 et 120).
    """
    conteneur = CONTENEURS.get(service)
    if conteneur is None:
        return {"erreur": f"service inconnu : {service}", "services_connus": list(CONTENEURS)}
    minutes = max(1, min(minutes, 120))  # on borne ce que le modèle demande
    proc = subprocess.run(
        ["docker", "logs", "--since", f"{minutes}m", conteneur],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        return {"erreur": "logs indisponibles", "detail": proc.stderr.strip()[:300]}

    erreurs = []
    for ligne in (proc.stdout + proc.stderr).splitlines():
        try:
            evenement = json.loads(ligne)
        except json.JSONDecodeError:
            continue  # lignes non JSON (messages d'uvicorn) ignorées
        if evenement.get("level") in ("ERROR", "CRITICAL"):
            erreurs.append(evenement)

    codes = Counter(e.get("error_code") or f"HTTP_{e.get('status')}" for e in erreurs)
    return {
        "service": service,
        "fenetre_minutes": minutes,
        "nb_erreurs": len(erreurs),
        "par_code": dict(codes),
        "exemples": erreurs[-3:],  # 3 exemples suffisent : on ne noie pas le modèle
    }
