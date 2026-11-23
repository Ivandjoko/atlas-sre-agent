"""Point d'entrée de Sentinelle sur AgentCore Runtime."""
import json
import os
from contextlib import ExitStack

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from opentelemetry import trace
from strands.tools.mcp import MCPClient

REGION = "eu-central-1"

# 1) Les secrets viennent de Secrets Manager, lus une fois au démarrage du conteneur
_brut = boto3.client("secretsmanager", region_name=REGION).get_secret_value(
    SecretId=os.environ["SENTINELLE_SECRET_ID"])["SecretString"]
SECRETS = json.loads(_brut)
for cle in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
    os.environ[cle] = SECRETS[cle]

from sentinelle import creer_agent          # noqa: E402  (après le chargement des secrets)
from telemetrie import activer_telemetrie   # noqa: E402

activer_telemetrie()
app = BedrockAgentCoreApp()


def fabriquer_clients() -> dict[str, MCPClient]:
    """Les trois serveurs MCP, tous joints en HTTP avec un jeton."""
    return {
        "mcp-ops-atlas": MCPClient(
            url=os.environ["MCP_OPS_URL"],
            headers={"Authorization": f"Bearer {SECRETS['MCP_OPS_TOKEN']}"}),
        "github": MCPClient(
            url="https://api.githubcopilot.com/mcp/",
            headers={"Authorization": f"Bearer {SECRETS['GITHUB_PAT']}",
                     "X-MCP-Toolsets": "issues"}),
        "slack": MCPClient(
            url=os.environ["SLACK_MCP_URL"],
            headers={"Authorization": f"Bearer {SECRETS['SLACK_MCP_API_KEY']}"}),
    }


@app.entrypoint
def invoke(payload):
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():   # recommandation de sécurité AWS
        return {"erreur": "le champ 'prompt' doit être un texte non vide"}

    with ExitStack() as pile:
        outils, indisponibles = [], []
        for nom, client in fabriquer_clients().items():
            try:
                pile.enter_context(client)
                outils += client.list_tools_sync()
            except Exception as exc:                          # un serveur en panne ne bloque pas l'enquête
                indisponibles.append(nom)
                print(json.dumps({"niveau": "ERROR", "serveur_mcp": nom, "erreur": str(exc)[:300]}))
        note = (f"\n\nATTENTION : serveurs MCP indisponibles : {', '.join(indisponibles)}. "
                "Signale-le dans ta réponse et indique ce que tu n'as pas pu faire.") if indisponibles else ""

        agent = creer_agent(outils, silencieux=True, session_id=payload.get("session_id"), note_systeme=note)
        resultat = agent(prompt)

    fournisseur = trace.get_tracer_provider()
    if hasattr(fournisseur, "force_flush"):
        fournisseur.force_flush()
    return {"reponse": str(resultat), "serveurs_indisponibles": indisponibles,
            "tokens": resultat.metrics.accumulated_usage}


if __name__ == "__main__":
    app.run()   # écoute sur 0.0.0.0:8080, routes /invocations et /ping
