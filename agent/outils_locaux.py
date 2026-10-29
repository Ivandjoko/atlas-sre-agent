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
    """Résume le trafic récent d'un service : nombre de requêtes, taux d'échec,
    et causes des échecs regroupées par code d'erreur, avec quelques exemples.

    Args:
        service: nom du service, par exemple "api-virements".
        minutes: fenêtre d'analyse en minutes (entre 1 et 120).
    """
    conteneur = CONTENEURS.get(service)
    if conteneur is None:
        return {"erreur": f"service inconnu : {service}", "services_connus": list(CONTENEURS)}
    minutes = max(1, min(minutes, 120))
    proc = subprocess.run(
        ["docker", "logs", "--since", f"{minutes}m", conteneur],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        return {"erreur": "logs indisponibles", "detail": proc.stderr.strip()[:300]}

    acces, causes = [], []
    for ligne in (proc.stdout + proc.stderr).splitlines():
        try:
            evt = json.loads(ligne)
        except json.JSONDecodeError:
            continue
        chemin = evt.get("path", "")
        if evt.get("message") == "requête traitée":
            # On exclut les sondes et le chaos : ce n'est pas du trafic client
            if chemin in ("/health", "/ready") or chemin.startswith("/chaos"):
                continue
            acces.append(evt)
        elif evt.get("error_code"):
            causes.append(evt)

    echecs = [e for e in acces if e.get("status", 0) >= 500]
    taux = round(100 * len(echecs) / len(acces), 1) if acces else 0.0
    return {
        "service": service,
        "fenetre_minutes": minutes,
        "requetes_clients": len(acces),
        "requetes_en_echec": len(echecs),
        "taux_echec_pct": taux,
        "echecs_par_statut": dict(Counter(f"HTTP_{e['status']}" for e in echecs)),
        "causes_par_code": dict(Counter(e["error_code"] for e in causes)),
        "exemples_causes": causes[-3:],
    }
