import json
import os
import sys

from strands import Agent
from strands.models import BedrockModel

from outils_locaux import lire_logs_erreurs, verifier_sante
from skills import catalogue_skills, charger_skill, lire_ressource_skill

MODEL_ID = os.getenv("SENTINELLE_MODEL_ID", "eu.anthropic.claude-sonnet-4-6")

PROMPT_BASE = """Tu es Sentinelle, l'agent SRE de la Banque Atlas.
Services surveillés : api-virements uniquement. Si on te parle d'un autre service,
dis qu'il n'est pas surveillé, sans appeler d'outil.

Règles permanentes :
- Appuie chaque affirmation sur un résultat d'outil. N'invente jamais un chiffre ni un service.
- Tu ne peux rien modifier : tu observes et tu recommandes.
- Pas de tableau ni d'emoji. Réponds en français.

Skills : ce sont les procédures maison de la banque. Le catalogue ci-dessous ne donne
que leur nom et quand les utiliser. Dès qu'une demande correspond à une skill,
appelle charger_skill avec son nom AVANT d'agir, puis suis ses instructions.

Catalogue des skills :
{catalogue}"""


def creer_agent() -> Agent:
    model = BedrockModel(model_id=MODEL_ID, region_name="eu-central-1", temperature=0.2, max_tokens=4096)
    return Agent(
        model=model,
        system_prompt=PROMPT_BASE.format(catalogue=catalogue_skills()),
        tools=[verifier_sante, lire_logs_erreurs, charger_skill, lire_ressource_skill],
    )


def afficher_bilan(resultat) -> None:
    m = resultat.metrics
    print("\n\n=== Bilan ===")
    print("Tours de boucle :", m.cycle_count)
    print("Outils appelés  :", {nom: t.call_count for nom, t in m.tool_metrics.items()})
    print("Tokens          :", m.accumulated_usage)


if __name__ == "__main__":
    agent = creer_agent()
    if len(sys.argv) > 1:                      # mode une question
        afficher_bilan(agent(sys.argv[1]))
    else:                                      # mode conversation
        print("Sentinelle prête. Tape 'fin' pour quitter.")
        while (question := input("\nToi > ").strip()) not in ("", "fin"):
            afficher_bilan(agent(question))
    with open("conversation.json", "w") as f:
        json.dump(agent.messages, f, indent=2, ensure_ascii=False, default=str)
