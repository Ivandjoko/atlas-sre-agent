import json
import os
import sys
import uuid
from telemetrie import activer_telemetrie

from strands import Agent
from strands.models import BedrockModel

from connexions_mcp import client_github, client_ops, client_slack

from threading import Lock

from strands.hooks import BeforeInvocationEvent, BeforeToolCallEvent, HookProvider, HookRegistry

from skills import catalogue_skills, charger_skill, lire_ressource_skill

MODEL_ID = os.getenv("SENTINELLE_MODEL_ID", "eu.anthropic.claude-sonnet-4-6")

PROMPT_BASE = """Tu es Sentinelle, l'agent SRE de la Banque Atlas.
Services surveillés : api-virements uniquement. Si on te parle d'un autre service,
dis qu'il n'est pas surveillé, sans appeler d'outil.


Règles permanentes :
- Appuie chaque affirmation sur un résultat d'outil. N'invente jamais un chiffre ni un service.
- Sur les systèmes de la banque, tu ne peux rien modifier : tu observes et tu recommandes.
- Tes seules actions d'écriture : créer ou commenter une issue dans Ivandjoko/atlas-incidents,
  et poster dans #incidents, en suivant la skill notification-incident.
- Si un outil échoue ou est injoignable, dis-le explicitement. Ne présente jamais d'anciens résultats comme actuels.
- Pas de tableau ni d'emoji. Réponds en français.
- Si une skill demande un outil absent de ta liste, dis-le et arrête-toi. Ne recharge jamais une skill déjà chargée.

Skills : ce sont les procédures maison de la banque. Le catalogue ci-dessous ne donne
que leur nom et quand les utiliser. Dès qu'une demande correspond à une skill,
appelle charger_skill avec son nom AVANT d'agir, puis suis ses instructions.

Catalogue des skills :
{catalogue}"""


# 2) Nouvelle version de creer_agent : identifiant de session et mode silencieux (pour les tests)
def creer_agent(outils_mcp: list, silencieux: bool = False, session_id: str | None = None) -> Agent:
    model = BedrockModel(model_id=MODEL_ID, region_name="eu-central-1", temperature=0.2, max_tokens=4096)
    options = {
        "trace_attributes": {
            "session.id": session_id or f"local-{uuid.uuid4().hex[:8]}",
            "user.id": "ivan",
        }
        "hooks": [LimiteurOutils()],
    }
    if silencieux:
        options["callback_handler"] = None   # pas d'affichage au fil de l'eau
    return Agent(
        model=model,
        system_prompt=PROMPT_BASE.format(catalogue=catalogue_skills()),
        tools=[*outils_mcp, charger_skill, lire_ressource_skill],
        **options,
    )

def afficher_bilan(resultat) -> None:
    m = resultat.metrics
    print("\n\n=== Bilan ===")
    print("Tours de boucle :", m.cycle_count)
    print("Outils appelés  :", {nom: t.call_count for nom, t in m.tool_metrics.items()})
    print("Tokens          :", m.accumulated_usage)


class LimiteurOutils(HookProvider):
    """Garde-fou de coût : arrête l'agent s'il appelle trop d'outils pendant une même question."""

    def __init__(self, max_par_outil: int = 4, max_total: int = 15):
        self.max_par_outil, self.max_total = max_par_outil, max_total
        self.compteurs: dict[str, int] = {}
        self.total = 0
        self._verrou = Lock()

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.reinitialiser)
        registry.add_callback(BeforeToolCallEvent, self.verifier)

    def reinitialiser(self, event: BeforeInvocationEvent) -> None:
        with self._verrou:
            self.compteurs, self.total = {}, 0

    def verifier(self, event: BeforeToolCallEvent) -> None:
        nom = event.tool_use["name"]
        with self._verrou:
            self.compteurs[nom] = self.compteurs.get(nom, 0) + 1
            self.total += 1
            depasse = self.compteurs[nom] > self.max_par_outil or self.total > self.max_total
        if depasse:
            # 1) annule cet appel (le modèle reçoit un message d'erreur à la place du résultat)
            event.cancel_tool = (f"Limite atteinte ({nom}). N'appelle plus aucun outil : "
                                 "rédige ta conclusion avec les informations déjà obtenues.")
            # 2) empêche le tour suivant de démarrer
            event.invocation_state.setdefault("request_state", {})["stop_event_loop"] = True



if __name__ == "__main__":
    activer_telemetrie()
    ops, github, slack = client_ops(), client_github(), client_slack()
    with ops, github, slack:
        outils_mcp = [*ops.list_tools_sync(), *github.list_tools_sync(), *slack.list_tools_sync()]
        print(f"{len(outils_mcp)} outils MCP découverts")
        agent = creer_agent(outils_mcp)
        if len(sys.argv) > 1:
            afficher_bilan(agent(sys.argv[1]))
        else:
            print("Sentinelle prête. Tape 'fin' pour quitter.")
            while (question := input("\nToi > ").strip()) not in ("", "fin"):
                afficher_bilan(agent(question))
        with open("conversation.json", "w") as f:
            json.dump(agent.messages, f, indent=2, ensure_ascii=False, default=str)
