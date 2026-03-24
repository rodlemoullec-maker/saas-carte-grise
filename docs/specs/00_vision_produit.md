# Vision Produit — SaaS Carte Grise

## Problème résolu

Les professionnels de l'automobile (garages, concessions, revendeurs) traitent des demandes de carte grise répétitives, chronophages et sujettes à erreurs. Le dépôt en préfecture ou via ANTS génère des rejets fréquents dus à des incohérences documentaires non détectées à la source.

## Proposition de valeur

Automatiser au maximum la collecte, la validation et la soumission des dossiers de carte grise, en détectant les erreurs **avant** la soumission au SIV, réduisant les rejets à quasi-zéro.

## Utilisateurs cibles

| Profil | Rôle dans le système |
|--------|----------------------|
| **Pro habilité** (gérant, agent accrédité) | Soumet les dossiers, valide les cas ambigus |
| **Commercial** (vendeur en concession) | Déclenche la demande, collecte les documents |
| **Client particulier** | Fournit ses documents via lien sécurisé |
| **Admin SaaS** | Gestion des comptes, monitoring, config |

## Périmètre V1

- Cas : **Vente véhicule neuf, professionnel → particulier**
- Pipeline : collecte → OCR → validation → croisements → décision → soumission SIV
- Interface agent habilité pour les dossiers nécessitant revue manuelle
- Notifications automatiques (email/SMS) vers le professionnel et le client

## Périmètre V2+

- Véhicule d'occasion (pro→particulier, particulier→particulier)
- Changement d'adresse, duplicata, changement de titulaire
- Portail client dédié (upload documents en autonomie)
- Multi-tenants (plusieurs garages/concessions)
- Intégration DMS (logiciels de gestion garage)

## Indicateurs de succès

| KPI | Cible V1 |
|-----|----------|
| Taux de traitement automatique (sans intervention agent) | > 70% |
| Taux de rejet SIV | < 2% |
| Délai de traitement auto (hors soumission SIV) | < 5 minutes |
| Délai de revue agent | < 2h ouvrées |
| Taux de détection fraude (faux positifs) | < 0.5% |

## Contraintes réglementaires

- L'agent habilité porte la responsabilité légale de chaque dossier soumis au SIV
- Données personnelles soumises au RGPD — durée de conservation limitée, droit à l'oubli
- Les documents originaux ou copies conformes sont exigés — les photocopies dégradées sont refusées
- Toute action sur un dossier doit être tracée et horodatée (audit trail)
- Aucune donnée SIV ne doit transiter en clair — chiffrement en transit et au repos obligatoire
