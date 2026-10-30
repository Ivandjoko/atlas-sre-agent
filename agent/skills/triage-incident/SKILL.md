---
name: triage-incident
description: Procédure de la Banque Atlas pour enquêter sur un incident de production, classer sa sévérité (SEV1 à SEV4) et produire le diagnostic. À utiliser dès qu'une alarme, une panne ou des erreurs clients sont signalées.
---
# Triage d'incident — Banque Atlas

## Étapes
1. Mesurer : appeler verifier_sante et lire_logs_erreurs sur le service concerné (en parallèle).
   Si 0 requête en échec alors qu'un incident est signalé, relire les logs sur 120 minutes avant de conclure.
2. Classer la sévérité : lire la ressource references/matrice-severite.md de cette skill
   et l'appliquer au taux d'échec mesuré. Ne jamais classer de mémoire.
3. Identifier la cause probable à partir des codes d'erreur connus ci-dessous.
4. Rédiger le diagnostic au format imposé.

## Codes d'erreur connus
- CORE_BANKING_TIMEOUT : le core banking (système central des comptes) ne répond pas à temps. Équipe : Core Banking.
- CONFIG_MISSING : configuration absente au démarrage (secret ou variable). Équipe : Plateforme.
- CRASH_INJECTED : arrêt volontaire lors d'un test de chaos. Vérifier avec l'équipe SRE qu'un test est en cours.
- Code inconnu : le signaler tel quel, équipe à déterminer.

## Format du diagnostic (obligatoire, rien d'autre)
Incident : <service> — <SEVx>
Symptôme : <ce que vivent les clients, avec le taux d'échec chiffré>
Cause probable : <cause, avec le code d'erreur>
Preuves : <résultats d'outils précis>
Équipe à prévenir : <équipe responsable du code d'erreur>
Action recommandée : <1 à 3 actions>
Conformité : <si SEV1 : "Incident potentiellement majeur au sens de DORA : prévenir la conformité pour la classification et la notification réglementaire." Sinon : "Pas d'escalade conformité requise.">

