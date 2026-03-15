---
name: carte-grise-email-poll
description: Vérifie les nouveaux emails, filtre les expéditeurs autorisés, traite les dossiers automatiquement. Les résultats apparaissent dans le dashboard. Aucun email n'est envoyé sans validation de l'opérateur.
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Polling email et traitement automatique

Ce skill est le point d'entrée principal d'OpenClaw.
Il fait un cycle complet : vérifie les emails → filtre → traite → prépare les réponses.

## IMPORTANT
- Seuls les emails des expéditeurs listés dans `config/expediteurs_autorises.txt` sont traités
- Les emails des expéditeurs non autorisés sont IGNORÉS
- Aucun email de réponse n'est envoyé — tout est préparé dans le dashboard
- L'opérateur DOIT valider avant tout envoi

## Exécution

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 -c "
import sys; sys.path.insert(0, '.')
from src.pipeline.email_loop import process_once
process_once()
"
```

## Ce que fait le script

1. Se connecte à la boîte email (IMAP)
2. Récupère les emails non lus avec pièces jointes
3. Pour chaque email :
   - Vérifie si l'expéditeur est dans la liste autorisée
   - Si NON → ignore l'email, affiche un message
   - Si OUI → sauvegarde les PJ dans un dossier
4. Pour chaque dossier créé :
   - Classifie les documents (IA vision)
   - Extrait le texte par OCR
   - Structure les données en JSON
   - Recherche le véhicule dans la base
   - Vérifie la cohérence entre documents
   - Calcule les taxes selon la région (code postal)
   - Génère le CERFA 13750 pré-rempli
5. Le dossier apparaît dans le dashboard avec :
   - Statut "pret" si tout est OK → opérateur valide et envoie le CERFA
   - Statut "documents_manquants" si problème → email de relance pré-rempli à copier

## Résultat

Le résultat de chaque dossier traité est affiché dans le terminal :
- ✓ Dossier prêt — CERFA généré
- ⚠ Dossier incomplet — documents manquants détaillés
- ✗ Expéditeur non autorisé — ignoré
