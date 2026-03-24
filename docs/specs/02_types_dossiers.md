# Types de Dossiers — Vue d'ensemble

Ce fichier décrit tous les types de dossiers prévus dans le système.
Chaque type aura sa propre spec détaillée dans ce répertoire.

## Matrice des types

| Code | Libellé | Documents clés | Statut spec |
|------|---------|---------------|-------------|
| `NEUF_PRO_PARTICULIER` | Vente neuf, pro → particulier | COC, Facture, CNI, Domicile, Permis, Assurance | Complète → `01_regles_metier_neuf.md` |
| `OCCASION_PRO_PARTICULIER` | Vente occasion, pro → particulier | CG originale, CERFA 15776, Facture, CNI, Domicile, Permis, Assurance, Contrôle technique | A rédiger |
| `OCCASION_PART_PARTICULIER` | Cession entre particuliers | CG originale, CERFA 15776, Déclaration de cession, CNI, Domicile, Permis, Assurance, Contrôle technique | A rédiger |
| `CHANGEMENT_ADRESSE` | Mise à jour domicile | CG originale, CNI, Domicile | A rédiger |
| `DUPLICATA` | Perte ou vol CG | Déclaration perte/vol, CNI, Domicile | A rédiger |
| `CHANGEMENT_TITULAIRE` | Héritage / Divorce / Donation | Acte notarié ou jugement, CNI, Domicile, Permis, Assurance | A rédiger |
| `CONVERSION_ENERGIE` | Transformation (ex: GNV retrofit) | Certificat transformation, CG originale, Réception VTP | A rédiger |

## Différences clés entre types

### Neuf vs Occasion

| Critère | Neuf | Occasion |
|---------|------|---------|
| Carte grise existante | Non | Oui (à barrer) |
| COC requis | Oui | Non (déjà traité) |
| CERFA 15776 | Non | Oui |
| Déclaration de cession | Non | Oui |
| Contrôle technique | Non (neuf) | Oui si > 4 ans |
| VIN dans SIV | Doit être absent | Doit être présent et cohérent |

### Pro vs Particulier (vendeur)

| Critère | Vendeur pro | Vendeur particulier |
|---------|-------------|---------------------|
| SIRET requis | Oui | Non |
| Kbis utile | Oui | Non |
| TVA sur facture | Oui (20%) | Non (cession) |
| Déclaration de cession | Non (facture suffit) | Oui (CERFA 15776) |
