import json
import sys

from strands import Agent
from strands.models import BedrockModel

from outils_locaux import lire_logs_erreurs, verifier_sante

SYSTEM_PROMPT = """Tu es Sentinelle, l'agent SRE de la Banque Atlas.
Ta mission : diagnostiquer les incidents sur les services de la banque.

Règles :
- Appuie chaque affirmation sur un résultat d'outil. N'invente jamais un chiffre.
- Commence par vérifier la santé du service, puis analyse ses logs d'erreurs.
- Termine par un diagnostic au format :
  Service : ...
  Symptôme : ...
  Cause probable : ...
  Preuves : ...
  Action recommandée : ...
- Tu ne peux rien modifier : tu observes et tu recommandes.
- Réponds en français."""

model = BedrockModel(
    model_id="eu.anthropic.claude-sonnet-4-6",
    region_name="eu-central-1",
    temperature=0.2,
    max_tokens=2048,
)

agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=[verifier_sante, lire_logs_erreurs])

question = sys.argv[1] if len(sys.argv) > 1 else "Des clients signalent des échecs de virement. Enquête."
resultat = agent(question)

# --- Ce qui s'est passé sous le capot -----------------------------------------
m = resultat.metrics
print("\n\n=== Bilan ===")
print("Raison de l'arrêt     :", resultat.stop_reason)
print("Tours de boucle       :", m.cycle_count)
print("Outils appelés        :", {nom: t.call_count for nom, t in m.tool_metrics.items()})
print("Tokens (entrée/sortie) :", m.accumulated_usage)

# Toute la conversation, y compris les demandes d'outils et leurs résultats
with open("conversation.json", "w") as f:
    json.dump(agent.messages, f, indent=2, ensure_ascii=False, default=str)
