"""mcp-ops-atlas : serveur MCP d'exploitation de la Banque Atlas. Lecture seule."""
import json
import subprocess
import time
from collections import Counter

import boto3
import httpx
from botocore.exceptions import ClientError
from mcp.server import MCPServer

REGION = "eu-central-1"

# Catalogue des services surveillés : la seule source de vérité du serveur
SERVICES = {
    "api-virements": {
        "url": "http://localhost:8080",
        "conteneur": "api",
        "log_group": "/atlas/api-virements",
    },
}

mcp = MCPServer("mcp-ops-atlas")
logs = boto3.client("logs", region_name=REGION)


# --- Logique métier pure (sans réseau) : facile à tester ---------------------
def resumer_evenements(evenements: list[dict], minutes: int) -> dict:
    """Calcule trafic client, taux d'échec et causes à partir d'événements de log JSON."""
    acces, causes = [], []
    for evt in evenements:
        chemin = evt.get("path", "")
        if evt.get("message") == "requête traitée":
            if chemin in ("/health", "/ready") or chemin.startswith("/chaos"):
                continue  # sondes et chaos : pas du trafic client
            acces.append(evt)
        elif evt.get("error_code"):
            causes.append(evt)
    echecs = [e for e in acces if int(e.get("status", 0)) >= 500]
    taux = round(100 * len(echecs) / len(acces), 1) if acces else 0.0
    return {
        "fenetre_minutes": minutes,
        "requetes_clients": len(acces),
        "requetes_en_echec": len(echecs),
        "taux_echec_pct": taux,
        "echecs_par_statut": dict(Counter(f"HTTP_{e['status']}" for e in echecs)),
        "causes_par_code": dict(Counter(e["error_code"] for e in causes)),
        "exemples_causes": causes[:3],
    }


# --- Resource : données en lecture, pour l'application ou l'utilisateur -------
@mcp.resource("atlas://services")
def catalogue_services() -> str:
    """Catalogue des services surveillés par Sentinelle et leurs groupes de logs."""
    return json.dumps({nom: {"log_group": s["log_group"]} for nom, s in SERVICES.items()},
                      ensure_ascii=False)


# --- Tools : actions que le modèle peut déclencher -----------------------------
@mcp.tool()
def verifier_sante(service: str) -> dict:
    """Vérifie la santé d'un service de la Banque Atlas via ses sondes /health et /ready.

    Args:
        service: nom du service, par exemple "api-virements".
    """
    svc = SERVICES.get(service)
    if svc is None:
        return {"erreur": f"service inconnu : {service}", "services_connus": list(SERVICES)}
    resultat = {"service": service}
    for sonde in ("health", "ready"):
        try:
            resultat[sonde] = httpx.get(f"{svc['url']}/{sonde}", timeout=3).status_code
        except httpx.HTTPError as exc:
            resultat[sonde] = f"injoignable ({type(exc).__name__})"
    return resultat


@mcp.tool()
def etat_service(service: str) -> dict:
    """Donne l'état d'exécution d'un service : en marche ou non, code de sortie,
    nombre de redémarrages et date de démarrage.

    Args:
        service: nom du service, par exemple "api-virements".
    """
    svc = SERVICES.get(service)
    if svc is None:
        return {"erreur": f"service inconnu : {service}", "services_connus": list(SERVICES)}
    proc = subprocess.run(["docker", "inspect", svc["conteneur"]],
                          capture_output=True, text=True, timeout=10)
    if proc.returncode != 0:
        return {"service": service, "statut": "introuvable", "detail": proc.stderr.strip()[:200]}
    info = json.loads(proc.stdout)[0]
    etat = info["State"]
    return {
        "service": service,
        "plateforme": "docker (local)",
        "statut": etat["Status"],
        "en_marche": etat["Running"],
        "code_sortie": etat["ExitCode"],
        "redemarrages": info["RestartCount"],
        "demarre_le": etat["StartedAt"],
    }


REQUETE_INSIGHTS = """fields @message
| filter level in ["ERROR", "CRITICAL"] or message = "requête traitée"
| sort @timestamp desc
| limit 2000"""


@mcp.tool()
def lire_logs_erreurs(service: str, minutes: int = 15) -> dict:
    """Analyse les logs CloudWatch d'un service : nombre de requêtes clients, taux d'échec,
    et causes des échecs regroupées par code d'erreur, avec quelques exemples.

    Args:
        service: nom du service, par exemple "api-virements".
        minutes: fenêtre d'analyse en minutes (entre 1 et 120).
    """
    svc = SERVICES.get(service)
    if svc is None:
        return {"erreur": f"service inconnu : {service}", "services_connus": list(SERVICES)}
    minutes = max(1, min(minutes, 120))
    fin = int(time.time())
    try:
        query_id = logs.start_query(
            logGroupName=svc["log_group"], startTime=fin - minutes * 60, endTime=fin,
            queryString=REQUETE_INSIGHTS,
        )["queryId"]
    except ClientError as exc:
        return {"erreur": "CloudWatch inaccessible", "code": exc.response["Error"]["Code"]}

    # Logs Insights est asynchrone : on interroge jusqu'à ce que la requête soit terminée
    for _ in range(30):
        reponse = logs.get_query_results(queryId=query_id)
        if reponse["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
            break
        time.sleep(0.5)
    if reponse["status"] != "Complete":
        return {"erreur": f"requête Logs Insights : {reponse['status']}"}

    evenements = []
    for ligne in reponse["results"]:
        champs = {c["field"]: c["value"] for c in ligne}
        try:
            evenements.append(json.loads(champs.get("@message", "")))
        except json.JSONDecodeError:
            continue
    resume = resumer_evenements(evenements, minutes)
    resume["service"] = service
    resume["source"] = f"CloudWatch Logs Insights {svc['log_group']}"
    return resume


if __name__ == "__main__":
    # 127.0.0.1 : joignable uniquement depuis l'EC2 elle-même. On exposera en phase 7, avec un jeton.
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
