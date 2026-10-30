# Matrice de sévérité — Banque Atlas

Service critique : api-virements (paiements clients).

| Sévérité | Critère | Prise en charge |
| --- | --- | --- |
| SEV1 | Service indisponible (sondes en échec) ou taux d'échec >= 50 % | Immédiate, cellule de crise |
| SEV2 | Taux d'échec entre 10 % et 50 % | Sous 15 minutes, astreinte |
| SEV3 | Taux d'échec entre 1 % et 10 % | Sous 4 heures ouvrées |
| SEV4 | Taux d'échec inférieur à 1 %, aucun impact client | Ticket standard |

En cas de doute entre deux niveaux, choisir le plus élevé.
