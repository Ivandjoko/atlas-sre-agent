from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id="eu.anthropic.claude-sonnet-4-6",  # profil d'inférence EU
    region_name="eu-central-1",
    temperature=0.2,     # faible = réponses plus stables, utile pour un agent d'exploitation
    max_tokens=1024,     # plafond de la réponse : garde-fou de coût
)

agent = Agent(
    model=model,
    system_prompt="Tu es Sentinelle, l'agent SRE de la Banque Atlas. Tu réponds en français, brièvement.",
)

resultat = agent("Présente-toi en deux phrases.")
print("\n--- usage :", resultat.metrics.accumulated_usage)
