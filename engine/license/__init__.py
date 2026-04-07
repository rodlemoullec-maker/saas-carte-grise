"""
Système de licences AutoDoc Pro local.

Modèle de protection :
- Une paire de clés Ed25519 (privée chez l'éditeur, publique embarquée
  dans le logiciel local)
- Une licence = un payload JSON signé en Ed25519
- L'agent achète une licence, reçoit un fichier .key par email
- Il colle le contenu dans son interface AutoDoc Pro pour activer
- Le logiciel vérifie la signature avec la clé publique embarquée
- La licence est stockée localement (~/.autodoc-pro/license.key)

Mode essai :
- 30 jours sans clé requise au premier démarrage
- Marqueur stocké localement (date du premier lancement)
- Au bout de 30 jours, une licence valide est obligatoire

Aucun appel cloud n'est nécessaire pour vérifier une licence existante :
la signature cryptographique permet une validation 100% offline.
"""
