---
name: notification-incident
description: Procédure pour déclarer un incident diagnostiqué - issue GitHub dans atlas-incidents et alerte Slack dans #incidents, sans doublon. À utiliser après un triage, ou quand on demande d'ouvrir un ticket, de déclarer ou de notifier un incident.
---
# Déclaration d'incident — Banque Atlas

Préalable : un diagnostic au format de la skill triage-incident doit exister dans la conversation.
Sinon, faire d'abord le triage.

Dépôt : Ivandjoko/atlas-incidents. Canal Slack : #incidents (ID C0CCFRQRRJT).

## Étapes
1. Éviter les doublons : lister les issues OUVERTES du dépôt portant le label "incident".
   S'il en existe une pour le même service et le même code d'erreur, y ajouter un commentaire
   avec le nouveau diagnostic, au lieu de créer une issue.
2. Sinon, créer une issue :
   - titre : "[SEVx] <service> — <code d'erreur>"
   - corps : le diagnostic complet, puis la ligne "Diagnostic produit automatiquement par Sentinelle, à valider par l'astreinte."
   - labels : "incident" et la sévérité en minuscules ("sev2").
3. Poster dans #incidents un message court : sévérité, service, symptôme en une phrase,
   équipe à prévenir, lien de l'issue. Jamais de logs bruts ni de données client.
4. Si une étape échoue, le dire clairement. Ne jamais affirmer qu'une notification a été faite si l'outil a échoué.
5. Terminer par : lien de l'issue (créée ou commentée) et statut du message Slack.

## Cohérence (obligatoire)
- Si la sévérité change par rapport à l'issue existante : mettre à jour EN MÊME TEMPS le titre ET
  les labels (retirer l'ancien sevX, ajouter le nouveau), puis ajouter un commentaire
  "Sévérité modifiée : SEVa -> SEVb, parce que ...".
- Le titre, le label et le corps doivent toujours indiquer la même sévérité.
- Séparer l'état actuel de l'historique : si le service est injoignable, c'est le constat principal.
  Les statistiques de logs passées sont présentées comme "historique (avant la panne)".
- Un message Slack SEV1 contient toujours la ligne de conformité DORA du diagnostic.
